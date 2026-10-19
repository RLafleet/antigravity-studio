import os
import sys
import time
from playwright.sync_api import sync_playwright

# Ensure UTF-8 stdout on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from slice_spritesheet import slice_spritesheet

PROFILE_DIR = os.path.expanduser(r"~/.antigravity_studio/playwright_studio_profile")
RAW_SHEET_PATH = os.path.abspath(r"assets/monsters/goblin_raw_sheet.png")

DEFAULT_PROMPT = (
    "2D video game animation sprite sheet of a skinny green goblin character with droopy tired eyes, "
    "wearing a ragged brown tunic and holding pink dumbbells. "
    "Generate 6 separate frames for an idle breathing animation cycle in a single horizontal strip. "
    "IMPORTANT: Each frame must be widely spaced apart with generous empty padding between characters, "
    "so arms, weapons and ears never touch or overlap. Solid bright red background #FF0000 for easy chroma key. "
    "Feet must remain firmly planted at the exact same ground level across all 6 frames."
)

def step_1_authenticate(p):
    """
    Launches browser for one-time interactive Google login if needed.
    """
    os.makedirs(PROFILE_DIR, exist_ok=True)
    print("=" * 65)
    print(" [1/3] ИНИЦИАЛИЗАЦИЯ БРАУЗЕРА PLAYWRIGHT")
    print(f"       Профиль: {PROFILE_DIR}")
    print("=" * 65)

    context = p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR,
        channel="msedge",
        headless=False,
        args=[
            "--start-maximized",
            "--no-first-run",
            "--no-default-browser-check"
        ]
    )

    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://aistudio.google.com/prompts/new_chat", timeout=60000)

    # Check if login is required
    time.sleep(3)
    if "accounts.google.com" in page.url or "welcome" in page.url:
        print("\n" + "!" * 65)
        print(" [!] ТРЕБУЕТСЯ ОДНОКРАТНЫЙ ВХОД В GOOGLE-АККАУНТ:")
        print("     В открывшемся окне браузера войдите под своим PRO-аккаунтом.")
        print("     Бот ожидает, пока откроется чат AI Studio...")
        print("!" * 65 + "\n")
        
        # Wait for user to log in and land on the AI Studio chat interface
        while "accounts.google.com" in page.url or "welcome" in page.url:
            time.sleep(2)
        
        print("[OK] Авторизация успешно завершена! Сессия сохранена в профиле бота.")
        time.sleep(3)

    return context, page

def step_2_send_prompt_via_dom(page, prompt=DEFAULT_PROMPT):
    """
    Locates prompt textarea via DOM selectors, fills it, and triggers generation.
    """
    print("\n" + "=" * 65)
    print(" [2/3] ОТПРАВКА ПРОМПТА ЧЕРЕЗ DOM")
    print("=" * 65)

    # Make sure we are on new_chat or chat page
    if "prompts" not in page.url:
        page.goto("https://aistudio.google.com/prompts/new_chat")
        time.sleep(3)

    # Potential DOM selectors for the AI Studio prompt input
    input_selectors = [
        'textarea[aria-label="Type something"]',
        'textarea[placeholder*="Type something"]',
        'textarea[placeholder*="prompt"]',
        'ms-autosize-textarea textarea',
        'div[contenteditable="true"]',
        'textarea.chat-input',
        'textarea'
    ]

    input_elem = None
    for sel in input_selectors:
        try:
            elem = page.wait_for_selector(sel, state="visible", timeout=4000)
            if elem:
                input_elem = elem
                print(f"[OK] Поле ввода найдено в DOM (селектор: '{sel}')")
                break
        except Exception:
            continue

    if not input_elem:
        raise RuntimeError("Не удалось обнаружить поле ввода в DOM Google AI Studio!")

    print("[*] Вставляем промпт в поле ввода через DOM API...")
    input_elem.fill(prompt)
    time.sleep(1)

    print("[*] Отправляем запрос на генерацию (Ctrl+Enter)...")
    input_elem.press("Control+Enter")
    print("[OK] Запрос отправлен! Ожидаем генерацию спрайта...")

def step_3_wait_and_download_image(page, output_path=RAW_SHEET_PATH):
    """
    Monitors DOM for the newly generated image element and downloads it.
    """
    print("\n" + "=" * 65)
    print(" [3/3] ОЖИДАНИЕ И СКАЧИВАНИЕ СПРАЙТА ИЗ DOM")
    print("=" * 65)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Track existing images before generation to detect the new one
    existing_imgs = page.query_selector_all("img")
    existing_srcs = set(img.get_attribute("src") or "" for img in existing_imgs)

    print(f"[*] Базовых изображений на странице: {len(existing_imgs)}")
    print("[*] Ожидаем появления нового сгенерированного спрайтшита (таймаут 3 минуты)...")

    target_img = None
    start_time = time.time()
    max_wait = 180  # 3 minutes

    while time.time() - start_time < max_wait:
        current_imgs = page.query_selector_all("img")
        for img in current_imgs:
            src = img.get_attribute("src") or ""
            # Must not be an existing image, avatar or UI icon
            if src not in existing_srcs and not any(k in src.lower() for k in ["avatar", "profile", "icon", "favicon"]):
                box = img.bounding_box()
                # Generated spritesheets are large (>200px)
                if box and box["width"] > 200 and box["height"] > 150:
                    target_img = img
                    print(f"[OK] Обнаружен сгенерированный спрайт! Размер: {int(box['width'])}x{int(box['height'])}")
                    break
        if target_img:
            break
        time.sleep(3)

    if not target_img:
        print("[!] Не удалось автоматически обнаружить новое изображение в DOM.")
        print("[*] Браузер остаётся открытым, чтобы вы могли сохранить изображение вручную.")
        return False

    print(f"[*] Скачиваем спрайт через DOM element screenshot...")
    target_img.screenshot(path=output_path)
    print(f"[OK] Спрайтшит сохранён: {output_path}")

    print("\n[*] Запуск автоматической нарезки (хромакей -> альфа-канал)...")
    preview_file = slice_spritesheet(output_path, num_frames=6, output_dir="assets/monsters/goblin_idle")
    print(f"[OK] Готово! Интерактивный плеер: {preview_file}")
    return True

def run():
    with sync_playwright() as p:
        context, page = step_1_authenticate(p)
        try:
            step_2_send_prompt_via_dom(page)
            success = step_3_wait_and_download_image(page)
            if success:
                print("\n" + "=" * 65)
                print(" 🎉 ПАЙПЛАЙН УСПЕШНО ЗАВЕРШЕН!")
                print("=" * 65)
        except Exception as e:
            print(f"\n[!] Ошибка в процессе автоматизации: {e}")
        finally:
            print("\n[*] Окно браузера остаётся открытым. Закройте его, когда закончите просмотр.")
            try:
                while not page.is_closed():
                    time.sleep(1)
            except Exception:
                pass
            context.close()

if __name__ == "__main__":
    run()
