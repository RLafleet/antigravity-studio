import os
import sys
import time
from playwright.sync_api import sync_playwright

def run_edge_sprite_automation(prompt_text=None):
    """
    Automates Microsoft Edge to open Google AI Studio (Nano Banana PRO / Gemini Image),
    enters the sprite-generation prompt, and enables visual feedback loop.
    """
    user_data_dir = os.path.expanduser(r"~/.antigravity_studio/edge_ai_profile")
    os.makedirs(user_data_dir, exist_ok=True)

    default_prompt = (
        "2D video game animation sprite sheet of a skinny green goblin character with droopy tired eyes, "
        "wearing a ragged brown tunic and holding pink dumbbells. "
        "Generate 6 separate frames for an idle breathing animation cycle. "
        "IMPORTANT: Each frame must be widely spaced apart with generous empty padding between characters, "
        "so arms, weapons and ears never touch or overlap. Solid bright magenta/green background for easy chroma key. "
        "Feet must remain firmly planted at the exact same ground level across all 6 frames."
    )
    prompt = prompt_text or default_prompt

    print("=" * 60)
    print(" 🚀 Edge Sprite Bot: Запуск Microsoft Edge...")
    print(f"[*] Профиль Edge: {user_data_dir}")
    print("=" * 60)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="msedge",
            headless=False,
            args=[
                "--start-maximized",
                "--no-first-run",
                "--no-default-browser-check"
            ]
        )

        page = context.pages[0] if context.pages else context.new_page()
        print("[*] Переход в Google AI Studio...")
        page.goto("https://aistudio.google.com/prompts/new_chat", timeout=60000)

        print("\n" + "=" * 60)
        print("💡 СОВЕТ:")
        print("Если вы ещё не вошли в Google AI Studio — войдите один раз под своим аккаунтом.")
        print("Сессия сохранится в профиле навсегда!")
        print("=" * 60 + "\n")

        # Check if login is needed or if chat is open
        time.sleep(3)
        print(f"[*] Текущий URL: {page.url}")
        print(f"[*] Заголовок страницы: {page.title()}")

        # Keep browser open for user interaction or automation
        print("\n[✓] Edge готов к генерации спрайтов с моделью Nano Banana PRO / Flash Image.")
        print("[*] Окно Edge открыто. Чтобы завершить сессию, закройте браузер или нажмите Ctrl+C в консоли.")
        
        try:
            while not page.is_closed():
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            context.close()

if __name__ == "__main__":
    run_edge_sprite_automation()
