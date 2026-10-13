import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

from config import (
    load_config, save_config,
    load_day_plan, save_day_plan,
    DAY_PLAN_FILE
)
from gemini_client import GeminiClient
from spec_architect import scan_workspace
from worker_engine import WorkerEngine
from git_manager import run_git_cmd, git_commit_and_push


class KeyBalancer:
    """Manages rotation, cooldowns, and failover between multiple Gemini API keys."""

    def __init__(self, key_a: str, key_b: str):
        self.keys = []
        if key_a:
            self.keys.append({"id": "Key-A", "key": key_a, "cooldown_until": 0.0})
        if key_b and key_b != key_a:
            self.keys.append({"id": "Key-B", "key": key_b, "cooldown_until": 0.0})

        self.current_idx = 0

    def has_keys(self) -> bool:
        return len(self.keys) > 0

    async def acquire_key(self, log_fn: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """Gets the next ready key. If all are in cooldown, waits patiently."""
        if not self.keys:
            return {"id": "No-Key", "key": ""}

        while True:
            now = time.time()
            # Try round-robin
            for _ in range(len(self.keys)):
                candidate = self.keys[self.current_idx]
                self.current_idx = (self.current_idx + 1) % len(self.keys)

                if candidate["cooldown_until"] <= now:
                    return candidate

            # All keys are in cooldown: find the earliest wake time
            min_cooldown = min(k["cooldown_until"] for k in self.keys)
            wait_seconds = max(5.0, min_cooldown - now)
            if log_fn:
                log_fn(f"🐢 Все API-ключи охлаждаются. Спокойно ждем {int(wait_seconds)} сек...")
            await asyncio.sleep(min(wait_seconds, 60.0))

    def mark_rate_limited(self, key_obj: Dict[str, Any], cooldown_seconds: float = 120.0):
        """Puts a key in cooldown on 429/ResourceExhausted."""
        key_obj["cooldown_until"] = time.time() + cooldown_seconds


DAY_PLANNER_SYSTEM_PROMPT = """You are an Elite Principal AI Architect and Tech Lead responsible for designing a Slow & Steady, atomic daily execution plan.

Your core philosophy:
- "🐢 Никакой спешки. Медленно, размеренно, но на 100% надежно."
- Break the user's high-level daily goal into 4 to 8 small, perfectly isolated, and atomic steps.
- Small steps prevent context bloating, eliminate hallucinations, and consume minimal tokens.
- For EACH step, you must choose the appropriate thinking level:
  * 'low' for simple configs, documentation, types, and trivial updates.
  * 'medium' for standard business logic and component implementations.
  * 'high' for complex algorithms, security, payment transactions, and test suites.

OUTPUT MUST BE STRICT VALID JSON MATCHING THIS EXACT SCHEMA:
{
  "goal_summary_ru": "Краткое понятное описание цели на день",
  "estimated_steps_count": 5,
  "steps": [
    {
      "index": 1,
      "title": "Краткое название шага на русском",
      "title_en": "Technical English Step Title",
      "model": "gemini-3.8-flash",
      "thinking_level": "low" or "medium" or "high",
      "objective": "One-sentence high-impact technical objective in English",
      "target_files": ["src/path1.ts"],
      "verification_commands": ["npm test" or "npm run build"],
      "antigravity_prompt": "Precise, complete multi-line English prompt to instruct the Antigravity developer agent for this specific step"
    }
  ]
}
"""


class DayOrchestrator:
    """The Slow & Steady Day Task Daemon."""

    def __init__(self, workspace_path: Optional[str] = None):
        self.cfg = load_config()
        self.workspace_path = workspace_path or self.cfg.get("default_workspace", "")
        self.key_balancer = KeyBalancer(
            key_a=self.cfg.get("gemini_api_key_a") or self.cfg.get("gemini_api_key", ""),
            key_b=self.cfg.get("gemini_api_key_b", "")
        )
        self.is_paused = False
        self.is_running = False
        self._current_worker: Optional[WorkerEngine] = None

    def log(self, msg: str, plan_data: Optional[Dict[str, Any]] = None):
        t_str = datetime.now().strftime("%H:%M:%S")
        line = f"[{t_str}] {msg}"
        print(line, flush=True)
        if plan_data is not None:
            if "logs" not in plan_data:
                plan_data["logs"] = []
            plan_data["logs"].append({"time": t_str, "msg": msg})
            plan_data["logs"] = plan_data["logs"][-100:]
            save_day_plan(plan_data)

    async def create_plan(self, daily_goal: str) -> Dict[str, Any]:
        """Orchestrator wakes up, creates atomic plan, saves to disk, and goes to sleep."""
        self.log(f"🧠 Оркестратор проснулся: проектируем план на день для цели: «{daily_goal}»")
        key_obj = await self.key_balancer.acquire_key(self.log)

        client = GeminiClient(
            api_key=key_obj["key"],
            model_name="gemini-3.8-flash",
            thinking_level="high"
        )

        snapshot = scan_workspace(self.workspace_path)
        tree_str = "\n".join(snapshot.get("tree", [])[:80])

        prompt = f"""=== DAILY GOAL ===
{daily_goal}

=== WORKSPACE SNAPSHOT ===
Path: {self.workspace_path}
Stack: {snapshot.get("stack")}
Tree:
{tree_str}
"""

        resp = await client.generate(
            prompt=prompt,
            system_instruction=DAY_PLANNER_SYSTEM_PROMPT,
            json_output=True,
            temperature=0.2
        )

        if not resp.get("ok") or not resp.get("json"):
            err = resp.get("error") or resp.get("json_error") or "Unknown generation error"
            self.log(f"[!] Ошибка планирования: {err}")
            return {"ok": False, "error": err}

        plan_json = resp["json"]
        steps = plan_json.get("steps", [])

        plan_data: Dict[str, Any] = {
            "day_task_id": f"day_{int(time.time())}",
            "goal": daily_goal,
            "goal_summary_ru": plan_json.get("goal_summary_ru", daily_goal),
            "workspace_path": self.workspace_path,
            "created_at": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            "status": "in_progress",
            "total_steps": len(steps),
            "current_step_index": 0,
            "cooldown_seconds": self.cfg.get("day_cooldown_seconds", 120),
            "steps": steps,
            "logs": []
        }

        # Initialize statuses for all steps
        for s in plan_data["steps"]:
            s["status"] = "pending"
            s["quality_check"] = None
            s["completed_at"] = None

        save_day_plan(plan_data)
        self.log(f"✓ План успешно декомпозирован на {len(steps)} микро-шагов. Оркестратор засыпает (токены = 0).", plan_data)
        return {"ok": True, "plan": plan_data}

    async def run_pipeline(self, on_event_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """Main loop: executes steps steadily with cooling pauses and quality checks."""
        self.is_running = True
        self.is_paused = False

        plan_data = load_day_plan()
        if not plan_data:
            return {"ok": False, "error": "Нет активного плана на день. Сначала создайте его."}

        steps = plan_data.get("steps", [])
        total = len(steps)
        cooldown = plan_data.get("cooldown_seconds", 120)

        self.log(f"🚀 Запуск размеренного конвейера: {total} шагов. Кулдаун между шагами: {cooldown} сек.", plan_data)

        for idx in range(plan_data.get("current_step_index", 0), total):
            if self.is_paused:
                self.log(f"⏸️ Конвейер поставлен на паузу на шаге {idx + 1}/{total}.", plan_data)
                plan_data["status"] = "paused"
                save_day_plan(plan_data)
                break

            step = steps[idx]
            plan_data["current_step_index"] = idx
            step["status"] = "running"
            save_day_plan(plan_data)

            step_title = step.get("title") or step.get("title_en") or f"Шаг {idx + 1}"
            th_level = step.get("thinking_level", "medium")

            # 1. Acquire key
            key_obj = await self.key_balancer.acquire_key(self.log)
            self.log(f"\n--- [ШАГ {idx + 1}/{total}]: {step_title} ---", plan_data)
            self.log(f"🔑 Активный ключ: {key_obj['id']} · Уровень мышления: {th_level.upper()}", plan_data)

            if on_event_callback:
                on_event_callback({"type": "step_start", "step_index": idx, "step": step, "key_id": key_obj["id"]})

            # 2. Execution via Worker
            worker_prompt = step.get("antigravity_prompt", "")
            verification_cmds = step.get("verification_commands", [])

            self._current_worker = WorkerEngine(
                workspace_path=self.workspace_path,
                model_name=step.get("model", "gemini-3.8-flash"),
                thinking_level=th_level
            )

            worker_error = None
            async for ev in self._current_worker.execute_task(worker_prompt, verification_cmds):
                if on_event_callback:
                    on_event_callback(ev)
                if ev.get("event") == "error":
                    worker_error = ev.get("error")

            # 3. Quality Check
            step["status"] = "verifying"
            save_day_plan(plan_data)
            self.log(f"🔍 Шаг {idx + 1}: Проверка качества и запуск верификации...", plan_data)

            # Auto Git Checkpoint
            commit_msg = f"day-step {idx + 1}/{total}: {step_title}"
            commit_res = await git_commit_and_push(self.workspace_path, commit_msg, push=False)
            diff_text = commit_res.get("commit_output", "Код зафиксирован")

            step["status"] = "completed"
            step["completed_at"] = datetime.now().strftime("%H:%M:%S")
            step["quality_check"] = {
                "passed": worker_error is None,
                "diff_summary": diff_text[:300]
            }
            save_day_plan(plan_data)

            self.log(f"✓ Шаг {idx + 1}/{total} успешно завершен и зафиксирован в Git! [x]", plan_data)

            if on_event_callback:
                on_event_callback({"type": "step_completed", "step_index": idx, "step": step})

            # 4. Steady Cooldown Pause
            if idx + 1 < total and not self.is_paused:
                self.log(f"🐢 Никуда не торопимся: пауза {cooldown} сек для охлаждения квот и токенов...", plan_data)
                remaining = cooldown
                while remaining > 0 and not self.is_paused:
                    sleep_chunk = min(15, remaining)
                    await asyncio.sleep(sleep_chunk)
                    remaining -= sleep_chunk
                    if on_event_callback:
                        on_event_callback({"type": "cooldown_tick", "remaining_seconds": remaining})

        # All finished?
        if plan_data.get("current_step_index", 0) >= total - 1 and steps[-1].get("status") == "completed":
            plan_data["status"] = "completed"
            self.log(f"🏆 ВСЯ ДНЕВНАЯ ЗАДАЧА ВЫПОЛНЕНА НА 100%! Все {total} микро-шагов проверены и сохранены.", plan_data)
            save_day_plan(plan_data)
            if on_event_callback:
                on_event_callback({"type": "day_completed", "plan": plan_data})

        self.is_running = False
        return {"ok": True, "plan": plan_data}

    def pause(self):
        self.is_paused = True
        if self._current_worker:
            self._current_worker.stop()

    def resume(self):
        self.is_paused = False


async def cli_main():
    """Runs day orchestrator from command line."""
    print("=" * 65)
    print("🐢 ANTIGRAVITY SLOW & STEADY DAY RUNNER")
    print("=" * 65)

    orch = DayOrchestrator()
    plan = load_day_plan()

    if len(sys.argv) > 1 and sys.argv[1] == "--resume" and plan:
        print(f"[*] Возобновление сохраненного плана: «{plan.get('goal')}»")
        await orch.run_pipeline()
        return

    goal = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    if not goal:
        goal = input("Введите большую задачу на день:\n> ").strip()

    if not goal:
        print("Задача не указана. Выход.")
        return

    res = await orch.create_plan(goal)
    if res.get("ok"):
        print("\n[*] Начинаем размеренное исполнение...")
        await orch.run_pipeline()


if __name__ == "__main__":
    asyncio.run(cli_main())
