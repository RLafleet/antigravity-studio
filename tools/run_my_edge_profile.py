import os
import sys
import time
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from slice_spritesheet import slice_spritesheet

USER_DATA_DIR = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data")
RAW_SHEET_PATH = os.path.abspath(r"assets/monsters/goblin_raw_sheet.png")

DEFAULT_PROMPT = (
    "2D video game animation sprite sheet of a skinny green goblin character with droopy tired eyes, "
    "wearing a ragged brown tunic and holding pink dumbbells. "
    "Generate 6 separate frames for an idle breathing animation cycle in a single horizontal strip. "
    "IMPORTANT: Each frame must be widely spaced apart with generous empty padding between characters, "
    "so arms, weapons and ears never touch or overlap. Solid bright red background #FF0000 for easy chroma key. "
    "Feet must remain firmly planted at the exact same ground level across all 6 frames."
)

def run_with_user_profile():
    print("=" * 65)
    print(" 🚀 ЗАПУСК БОТА С ВАШИМ ОСНОВНЫМ ПРОФИЛЕМ EDGE (Profile 1)")
    print(f"    Путь: {USER_DATA_DIR}")
    print("=" * 65)

    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                channel="msedge",
                headless=False,
                args=[
                    "--profile-directory=Profile 1",
                    "--start-maximized",
                    "--no-first-run"
                ]
            )
        except Exception as e:
            if "ProcessSingleton" in str(e) or "Lock file" in str(e):
                print("\n[!] ОШИБКА БЛОКИРОВКИ: Ваш Edge сейчас открыт.")
                print("    Пожалуйста, закройте окно Edge, чтобы бот мог загрузить ваш профиль!")
                return
            raise e

        page = context.pages[0] if context.pages else context.new_page()
        print("[*] Переходим в Google AI Studio с вашим PRO-аккаунтом...")
        page.goto("https://aistudio.google.com/prompts/new_chat", timeout=60000)
        time.sleep(3)

        print(f"[OK] Страница загружена! URL: {page.url}")
        print(f"     Заголовок: {page.title()}")

        # Check if already logged in
        if "welcome" in page.url or "accounts.google.com" in page.url:
            print("[!] Требуется подтверждение входа в аккаунте.")
        else:
            print("[OK] Вы уже успешно авторизованы под своим профилем!")

        # Find textarea via DOM
        print("[*] Поиск поля ввода промпта в DOM...")
        input_selectors = [
            'textarea[aria-label="Type something"]',
            'textarea[placeholder*="Type something"]',
            'textarea[placeholder*="prompt"]',
            'ms-autosize-textarea textarea',
            'div[contenteditable="true"]',
            'textarea'
        ]

        input_elem = None
        for sel in input_selectors:
            try:
                elem = page.wait_for_selector(sel, state="visible", timeout=4000)
                if elem:
                    input_elem = elem
                    print(f"[OK] Поле ввода найдено: '{sel}'")
                    break
            except Exception:
                continue

        if input_elem:
            print("[*] Вставляем промпт спрайтшита через DOM...")
            input_elem.fill(DEFAULT_PROMPT)
            time.sleep(1)
            print("[*] Отправляем запрос на генерацию (Ctrl+Enter)...")
            input_elem.press("Control+Enter")
            print("[OK] Запрос отправлен в генерацию!")

            # Wait for image
            print("[*] Ожидаем генерации спрайта в чате...")
            time.sleep(20)
            
            # Find generated image
            imgs = page.query_selector_all("img")
            target_img = None
            for img in imgs:
                src = img.get_attribute("src") or ""
                if not any(k in src.lower() for k in ["avatar", "profile", "icon", "favicon"]):
                    box = img.bounding_box()
                    if box and box["width"] > 200 and box["height"] > 150:
                        target_img = img
                        break

            if target_img:
                os.makedirs(os.path.dirname(RAW_SHEET_PATH), exist_ok=True)
                target_img.screenshot(path=RAW_SHEET_PATH)
                print(f"[OK] Спрайтшит успешно сохранён: {RAW_SHEET_PATH}")
                preview = slice_spritesheet(RAW_SHEET_PATH, num_frames=6, output_dir="assets/monsters/goblin_idle")
                print(f"[OK] Анимация нарезана: {preview}")

        print("\n[*] Сессия завершена. Браузер остаётся открытым для просмотра.")
        try:
            while not page.is_closed():
                time.sleep(1)
        except Exception:
            pass
        context.close()

if __name__ == "__main__":
    run_with_user_profile()
