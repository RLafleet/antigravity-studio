import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncGenerator

from config import (
    load_config, load_day_plan, save_day_plan
)

from gemini_client import GeminiClient

BOARD_STORAGE_DIR = Path.home() / ".antigravity_studio" / "board_room"
BOARD_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

TECH_LEAD_CHAT_FILE = BOARD_STORAGE_DIR / "tech_lead_chat.json"
DIRECTOR_CHAT_FILE = BOARD_STORAGE_DIR / "director_chat.json"
DEBATES_FILE = BOARD_STORAGE_DIR / "debates.json"

# --- SYSTEM PROMPTS ---

TECH_LEAD_SYSTEM_PROMPT = """Ты — Главный Архитектор и Техдир проекта (Principal Tech Lead & Software Architect).
Твоя цель: АБСОЛЮТНАЯ надежность, простота, устойчивость архитектуры и чистый код.

ТВОЙ ХАРАКТЕР И ПРАВИЛА ОБЩЕНИЯ:
1. НЕ БУДЬ «YES-MAN»! Никогда не поддакивай слепо. Если разработчик или инвестор предлагает идею, которая нерациональна, раздувает скоуп или создает дыру в безопасности — открыто, аргументированно критикуй её.
2. Говори кратко, емко, без корпоративной воды.
3. Оценивай риски: производительность (FPS, память), античит (защита от накрутки кликерами), сложность тестирования.
4. Предлагай лучший инженерный компромисс: как решить суть проблемы минимальным количеством кода и надежными инструментами.
5. Ты в курсе текущего плана на день и архитектуры репозитория.

ФОРМАТ ОТВЕТА:
- Вердикт (Одобряю / Скептичен / Категорически против)
- Технические риски и подводные камни
- Рекомендуемое прагматичное решение
"""

DIRECTOR_SYSTEM_PROMPT = """Ты — Коммерческий Директор и Главный Продакт-менеджер (Chief Product & Revenue Officer).
Твоя главная цель: ЗАРАБОТАТЬ НАМ ДЕНЕГ, увеличить удержание игроков (Retention) и конверсию в Telegram Stars.

ТВОЙ ХАРАКТЕР И ОТНОШЕНИЯ С ПОЛЬЗОВАТЕЛЕМ:
1. Пользователь — это твой главный Инвестор и Фаундер, которому ты абсолютно доверяешь и уважаешь как партнера.
2. Ты НЕ грубишь и не заискиваешь, а общаешься как сильный топ-менеджер: твердо, уверенно, рационально обосновывая каждое решение через деньги, LTV, психологию игроков и конверсии.
3. Ты мыслишь бизнес-категориями: офферы Stars, стримерские донаты, удержание на 1-й и 7-й день, виральные механики, FOMO, множители наград.
4. Если инвестор предлагает идею, которая убьет экономику или не принесет денег — ты рационально объясняешь почему, показываешь расчеты и предлагаешь более доходную альтернативу.
5. Ты умеешь ставить задачи Техдиру на понятном инженерном языке, не требуя невозможного, но добиваясь продуктового результата.

ФОРМАТ ОТВЕТА:
- Бизнес-оценка (Сколько денег / игроков это принесет или сбережет)
- Продуктовые механики (Психология игрока, офферы Stars, удержание)
- Конкретные предложения по монетизации
"""

DEBATE_PROMPT_TEMPLATE = """=== ТЕМА ОБСУЖДЕНИЯ ДЛЯ СОВЕТА ДИРЕКТОРОВ ===
{topic}

=== КОНТЕКСТ ПРОЕКТА ===
Текущий план на день: {plan_summary}
Файлы проекта: {files_summary}

Вы — два ключевых лидера проекта:
- [ДИРЕКТОР / БИЗНЕС]: отстаивает выручку, Stars, удержание и психологию пользователей.
- [ТЕХДИР / АРХИТЕКТУРА]: отстаивает стабильность, производительность, надежность кода и отсутствие багов.

Правило дебатов:
Общайтесь аргументированно. Не спорьте ради спора. Найдите оптимальный баланс между прибылью и надежностью.
Если компромисс найден, завершите реплику ключевым словом: [КОНСЕНСУС: краткое согласованное решение].
"""


def load_chat_history(role: str) -> List[Dict[str, Any]]:
    target = TECH_LEAD_CHAT_FILE if role == "tech_lead" else (DIRECTOR_CHAT_FILE if role == "director" else DEBATES_FILE)
    if target.exists():
        try:
            with open(target, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_chat_history(role: str, history: List[Dict[str, Any]]):
    target = TECH_LEAD_CHAT_FILE if role == "tech_lead" else (DIRECTOR_CHAT_FILE if role == "director" else DEBATES_FILE)
    try:
        with open(target, "w", encoding="utf-8") as f:
            json.dump(history[-80:], f, indent=2, ensure_ascii=False)
    except Exception:
        pass


class BoardRoom:
    """Manages AI Leadership personas: Tech Lead (Architect), Director (Revenue), and AI-to-AI Debates."""

    def __init__(self):
        self.cfg = load_config()
        self.client = GeminiClient(
            api_key=self.cfg.get("gemini_api_key_a") or self.cfg.get("gemini_api_key", ""),
            model_name="gemini-3.8-flash",
            thinking_level="high"
        )
        self.active_debate_running = False

    async def talk_to_role(self, role: str, user_message: str) -> Dict[str, Any]:
        """User chats with Tech Lead or Director."""
        history = load_chat_history(role)
        sys_prompt = TECH_LEAD_SYSTEM_PROMPT if role == "tech_lead" else DIRECTOR_SYSTEM_PROMPT

        # Attach workspace context & current plan
        plan = load_day_plan()
        plan_summary = f"Цель: {plan.get('goal', 'Нет плана')}, Шагов: {len(plan.get('steps', []))}" if plan else "Нет активного плана"

        # Format prompt with last few messages
        history_context = "\n".join([f"{m.get('sender')}: {m.get('text')}" for m in history[-6:]])

        full_prompt = f"""=== ТЕКУЩИЙ КОНТЕКСТ ПРОЕКТА ===
{plan_summary}

=== ПРЕДЫДУЩИЕ РЕПЛИКИ ДИАЛОГА ===
{history_context if history_context else "(Начало диалога)"}

=== СООБЩЕНИЕ ИНВЕСТОРА / РАЗРАБОТЧИКА ===
{user_message}
"""
        resp = await self.client.generate(
            prompt=full_prompt,
            system_instruction=sys_prompt,
            temperature=0.3,
            thinking_level="high"
        )

        reply_text = resp.get("text", "Извините, не удалось получить ответ от модели.")
        
        # Save history
        now_str = datetime.now().strftime("%H:%M")
        history.append({"sender": "Пользователь", "text": user_message, "time": now_str})
        history.append({
            "sender": "Техдир" if role == "tech_lead" else "Директор",
            "text": reply_text,
            "time": now_str,
            "model": resp.get("model_used", "gemini-3.8-flash-high")
        })
        save_chat_history(role, history)

        return {
            "ok": True,
            "role": role,
            "reply": reply_text,
            "model_used": resp.get("model_used", "gemini-3.8-flash-high"),
            "history": history
        }

    async def run_ai_debate(self, topic: str, max_rounds: int = 3) -> AsyncGenerator[Dict[str, Any], None]:
        """Runs autonomous AI-to-AI discussion between Director and Tech Lead."""
        self.active_debate_running = True
        plan = load_day_plan()
        plan_summary = f"Цель: {plan.get('goal', 'Нет плана')}, Шагов: {len(plan.get('steps', []))}" if plan else "Нет плана"

        debates_history = load_chat_history("debate")
        debate_id = f"debate_{int(datetime.now().timestamp())}"
        session_messages = []

        yield {
            "type": "start",
            "debate_id": debate_id,
            "topic": topic,
            "message": f"🏁 Начало совместного совета: Директор (Бизнес) ↔ Техдир (Архитектура)"
        }

        current_speaker = "director"
        previous_speech = f"Инвестор предложил тему: «{topic}». Выскажи свое продуктовое и финансовое видение."

        rounds_done = 0
        consensus_reached = False

        while self.active_debate_running and rounds_done < max_rounds * 2 and not consensus_reached:
            speaker_name = "Директор" if current_speaker == "director" else "Техдир"
            other_name = "Техдир" if current_speaker == "director" else "Директор"
            sys_prompt = DIRECTOR_SYSTEM_PROMPT if current_speaker == "director" else TECH_LEAD_SYSTEM_PROMPT

            prompt = f"""=== ДЕБАТЫ СОВЕТА ДИРЕКТОРОВ ===
Тема: {topic}
План проекта: {plan_summary}

Предыдущая реплика от {other_name}:
«{previous_speech}»

Твой ответ как {speaker_name}:
Отвечай аргументированно, прямо по делу. Оцени позицию коллеги и предложи встречное решение.
Если согласен и компромисс найден, напиши в конце: [КОНСЕНСУС: суть договоренности].
"""

            yield {
                "type": "thinking",
                "speaker": speaker_name,
                "message": f"{speaker_name} обдумывает ответ..."
            }

            resp = await self.client.generate(
                prompt=prompt,
                system_instruction=sys_prompt,
                temperature=0.3,
                thinking_level="high"
            )

            speech_text = resp.get("text", "...")
            now_str = datetime.now().strftime("%H:%M")

            msg_entry = {
                "speaker": speaker_name,
                "role": current_speaker,
                "text": speech_text,
                "time": now_str,
                "round": (rounds_done // 2) + 1
            }
            session_messages.append(msg_entry)

            yield {
                "type": "message",
                "speaker": speaker_name,
                "role": current_speaker,
                "text": speech_text,
                "time": now_str,
                "round": (rounds_done // 2) + 1
            }

            if "[КОНСЕНСУС" in speech_text:
                consensus_reached = True
                consensus_text = speech_text.split("[КОНСЕНСУС")[1].split("]")[0].replace(":", "").strip()
                yield {
                    "type": "consensus",
                    "consensus": consensus_text,
                    "message": f"🤝 ДОСТИГНУТ КОНСЕНСУС: {consensus_text}"
                }
                break

            previous_speech = speech_text
            current_speaker = "tech_lead" if current_speaker == "director" else "director"
            rounds_done += 1
            await asyncio.sleep(1.0)

        self.active_debate_running = False

        # Save to history
        debates_history.append({
            "id": debate_id,
            "topic": topic,
            "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "messages": session_messages,
            "consensus": consensus_reached
        })
        save_chat_history("debate", debates_history)

        yield {
            "type": "end",
            "debate_id": debate_id,
            "rounds_completed": (rounds_done // 2) + 1,
            "consensus_reached": consensus_reached
        }

    def stop_debate(self):
        """Emergency stop button for AI-to-AI debates."""
        self.active_debate_running = False

    async def apply_dialog_to_plan(self, role: str) -> Dict[str, Any]:
        """Applies recent decisions from chat or debate directly to day_plan.json."""
        plan = load_day_plan()
        if not plan:
            return {"ok": False, "error": "Нет активного плана на день для изменения."}

        history = load_chat_history(role)
        if not history:
            return {"ok": False, "error": f"История диалога с {role} пуста."}

        # Collect dialog transcript
        if role == "debate":
            last_debate = history[-1] if history else {}
            dialog_text = "\n".join([f"{m.get('speaker')}: {m.get('text')}" for m in last_debate.get("messages", [])])
        else:
            dialog_text = "\n".join([f"{m.get('sender')}: {m.get('text')}" for m in history[-10:]])

        replan_prompt = f"""=== СОВМЕСТНОЕ РЕШЕНИЕ ИТОГОВ ДИАЛОГА ===
Роль источника: {role}
История согласованных решений:
{dialog_text}

=== ТЕКУЩИЙ ПЛАН НА ДЕНЬ ===
Цель: {plan.get('goal')}
Текущий шаг: {plan.get('current_step_index', 0)}
Всего шагов: {len(plan.get('steps', []))}
Текущие шаги:
{json.dumps(plan.get('steps', []), indent=2, ensure_ascii=False)}

ЗАДАЧА ОРКЕСТРАТОРА:
Перестрой и обнови список шагов в плане с учетом согласованных в диалоге решений!
ВАЖНЫЕ ПРАВИЛА:
1. Шаги со статусом 'completed' НЕ ТРОГАЙ И НЕ УДАЛЯЙ. Сохрани их как есть.
2. Оставшиеся шаги со статусом 'pending' обнови, замени, удали лишние или добавь новые шаги, удовлетворяющие новому решению.
3. Верни СТРОГО валидный JSON следующей структуры:
{{
  "summary_of_changes_ru": "Краткое описание, что изменилось в плане на русском языке",
  "steps": [ ...полный обновленный список шагов с сохранением схемы (index, title, title_en, model, thinking_level, objective, target_files, verification_commands, antigravity_prompt, status)... ]
}}
"""
        resp = await self.client.generate(
            prompt=replan_prompt,
            json_output=True,
            temperature=0.2,
            thinking_level="high"
        )

        if not resp.get("ok") or not resp.get("json"):
            return {"ok": False, "error": resp.get("error") or "Не удалось перестроить план"}

        replan_data = resp["json"]
        new_steps = replan_data.get("steps", [])
        if not new_steps:
            return {"ok": False, "error": "Модель вернула пустой список шагов"}

        plan["steps"] = new_steps
        plan["total_steps"] = len(new_steps)
        if "logs" not in plan:
            plan["logs"] = []
        change_summary = replan_data.get("summary_of_changes_ru", "План скорректирован по итогам диалога")
        t_str = datetime.now().strftime("%H:%M:%S")
        plan["logs"].append({
            "time": t_str,
            "msg": f"⚡ ПЛАН ОБНОВЛЕН СОВЕТОМ ДИРЕКТОРОВ ({role}): {change_summary}"
        })
        save_day_plan(plan)

        return {
            "ok": True,
            "summary_of_changes_ru": change_summary,
            "total_steps": len(new_steps),
            "plan": plan
        }
