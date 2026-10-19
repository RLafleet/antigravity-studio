import os
import sys
import io
import time
import socket
import urllib.request

# Ensure UTF-8 stdout encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from playwright.sync_api import sync_playwright
from slice_spritesheet import slice_spritesheet

DEFAULT_PROMPT = (
    "2D video game animation sprite sheet of a skinny green goblin character with droopy tired eyes, "
    "wearing a ragged brown tunic and holding pink dumbbells. "
    "Generate 6 separate frames for an idle breathing animation cycle in a single horizontal strip. "
    "IMPORTANT: Each frame must be widely spaced apart with generous empty padding between characters, "
    "so arms, weapons and ears never touch or overlap. Solid bright red background for easy chroma key. "
    "Feet must remain firmly planted at the exact same ground level across all 6 frames."
)

def is_cdp_port_open(port=9222):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex(('127.0.0.1', port)) == 0

def run_ai_studio_generation(prompt=DEFAULT_PROMPT, output_path="assets/monsters/goblin_raw_sheet.png"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print("=" * 65)
    print(" [BOT] Google AI Studio (Nano Banana PRO) Runner")
    print("=" * 65)

    with sync_playwright() as p:
        browser = None
        context = None
        page = None

        if is_cdp_port_open(9222):
            print("[+] Обнаружен открытый порт отладки Edge (9222)!")
            print("[*] Подключаемся напрямую к вашей активной сессии...")
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            # Search for existing AI Studio tab
            for p_elem in context.pages:
                if "aistudio.google.com" in p_elem.url:
                    page = p_elem
                    print(f"[✓] Найдена открытая вкладка AI Studio: {page.url}")
                    break
            if not page:
                page = context.new_page()
                page.goto("https://aistudio.google.com/prompts/new_chat")
        else:
            profile_dir = os.path.expanduser("~/.antigravity_studio/edge_ai_profile")
            print(f"[*] Порт 9222 не найден. Запускаем Edge через выделенный профиль:")
            print(f"    {profile_dir}")
            context = p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                channel="msedge",
                headless=False,
                args=["--start-maximized", "--no-first-run", "--no-default-browser-check"]
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://aistudio.google.com/prompts/new_chat")

        page.bring_to_front()
        time.sleep(3)

        # Check if user needs to log in
        if "welcome" in page.url or "accounts.google.com" in page.url:
            print("\n" + "!" * 65)
            print("[!] ТРЕБУЕТСЯ ВХОД В GOOGLE-АККАУНТ:")
            print("Пожалуйста, нажмите 'Get Started / Sign In' в открывшемся окне Edge")
            print("и войдите под своим Google-аккаунтом с PRO доступом.")
            print("Бот терпеливо ждет перехода в интерфейс чата...")
            print("!" * 65 + "\n")
            
            # Wait for user to log in and reach the chat page
            while "welcome" in page.url or "accounts.google.com" in page.url:
                time.sleep(2)
            print("[OK] Успешный вход зафиксирован! Переходим к чату...")
            time.sleep(2)
            if "prompts" not in page.url:
                page.goto("https://aistudio.google.com/prompts/new_chat")
                time.sleep(3)

        print("[*] Поиск текстового поля ввода промпта в AI Studio...")
        # Common textarea selectors in Google AI Studio
        selectors = [
            'textarea[aria-label="Type something"]',
            'textarea[placeholder*="prompt"]',
            'textarea[placeholder*="Type something"]',
            'textarea.chat-input',
            'ms-autosize-textarea textarea',
            'div[contenteditable="true"]',
            'textarea'
        ]

        input_el = None
        for sel in selectors:
            try:
                el = page.wait_for_selector(sel, timeout=3000)
                if el and el.is_visible():
                    input_el = el
                    print(f"[OK] Найдено поле ввода (селектор: {sel})")
                    break
            except Exception:
                continue

        if not input_el:
            print("[!] Автоматический селектор не сработал. Ожидание клика пользователя в поле ввода...")
            print("[*] Вы можете сами кликнуть в поле промпта или ввести текст.")
            time.sleep(5)
        else:
            print(f"[*] Вбиваем промпт для спрайта гоблина...")
            input_el.fill(prompt)
            time.sleep(1)
            print("[*] Отправляем запрос (Ctrl+Enter)...")
            input_el.press("Control+Enter")

        print("[*] Запрос отправлен в Nano Banana PRO!")
        print("[*] Ожидаем завершения генерации изображения...")
        
        target_img_element = None
        img_src = None
        max_wait = 180 # 3 minutes
        start_t = time.time()
        
        while time.time() - start_t < max_wait:
            images = page.query_selector_all("img")
            for img in images:
                src = img.get_attribute("src") or ""
                if ("blob:" in src or "googleusercontent" in src or "data:image" in src) and not "avatar" in src and not "profile" in src and not "icon" in src:
                    box = img.bounding_box()
                    if box and box["width"] > 200 and box["height"] > 200:
                        img_src = src
                        target_img_element = img
                        print(f"[OK] Найдено сгенерированное изображение! Размер: {box['width']}x{box['height']}")
                        break
            if target_img_element:
                break
            time.sleep(3)

        if target_img_element:
            print(f"[*] Скачиваем итоговый спрайт...")
            target_img_element.screenshot(path=output_path)
            print(f"[OK] Спрайт сохранен: {output_path}")

            print("[*] Запускаем автоматическую нарезку и хромакей...")
            preview_file = slice_spritesheet(output_path, num_frames=6, output_dir="assets/monsters/goblin_idle")
            print(f"[OK] УСПЕХ! Анимация готова: {preview_file}")
        else:
            print("[!] Время ожидания генерации истекло или требуется ручной запуск в чате.")
            print("[*] Окно браузера остается открытым для вашего контроля.")

        print("=" * 65)
        print("[*] Браузер остаётся открытым. Чтобы завершить работу, закройте окно Edge.")
        try:
            while not page.is_closed():
                time.sleep(1)
        except Exception:
            pass
        return output_path

if __name__ == "__main__":
    run_ai_studio_generation()
