import sys
import os
import time
import ctypes
from ctypes import wintypes
import pyautogui
import pyperclip

# Ensure UTF-8 stdout
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from slice_spritesheet import slice_spritesheet

user32 = ctypes.windll.user32
pyautogui.FAILSAFE = False

DEFAULT_PROMPT = (
    "2D video game animation sprite sheet of a skinny green goblin character with droopy tired eyes, "
    "wearing a ragged brown tunic and holding pink dumbbells. "
    "Generate 6 separate frames for an idle breathing animation cycle in a single horizontal strip. "
    "IMPORTANT: Each frame must be widely spaced apart with generous empty padding between characters, "
    "so arms, weapons and ears never touch or overlap. Solid bright red background #FF0000 for easy chroma key. "
    "Feet must remain firmly planted at the exact same ground level across all 6 frames."
)

def attach_to_desktop():
    h_desk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
    if h_desk:
        user32.SetThreadDesktop(h_desk)

def find_edge_window():
    attach_to_desktop()
    target_hwnd = [None]
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    
    def enum_cb(hwnd, extra):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                if ("Google AI Studio" in title or "eddrianllamo" in title) and "Edge" in title:
                    target_hwnd[0] = hwnd
                    return False
        return True
        
    user32.EnumDesktopWindows(user32.GetThreadDesktop(ctypes.windll.kernel32.GetCurrentThreadId()), WNDENUMPROC(enum_cb), 0)
    return target_hwnd[0]

def bring_window_to_front(hwnd):
    attach_to_desktop()
    user32.ShowWindow(hwnd, 3) # SW_MAXIMIZE
    user32.SwitchToThisWindow(hwnd, True)
    time.sleep(1)

def run_automation(prompt=DEFAULT_PROMPT):
    print("=" * 65)
    print(" 🤖 АВТОНОМНЫЙ РОБОТ ДЛЯ GOOGLE AI STUDIO (NANO BANANA PRO)")
    print("=" * 65)
    
    print("[*] Поиск открытого окна Edge с Google AI Studio...")
    hwnd = find_edge_window()
    
    if not hwnd:
        print("[!] Окно Edge ещё не открыто на экране.")
        print("[*] Пожалуйста, нажмите один раз на значок Edge на панели задач.")
        print("[*] Бот ожидает появления окна в реальном времени...")
        while not hwnd:
            time.sleep(1)
            hwnd = find_edge_window()
        print(f"[OK] Окно Edge обнаружено! (HWND: {hwnd})")

    print("[*] Переводим окно в фокус...")
    bring_window_to_front(hwnd)
    time.sleep(1)

    # Click on the tab if needed (Google AI Studio tab)
    print("[*] Активируем вкладку Google AI Studio...")
    pyautogui.click(250, 20)
    time.sleep(1)

    # Focus prompt box (bottom center, ~ x=500, y=1065 on 1920x1200)
    print("[*] Фокусируемся на поле ввода промпта...")
    pyautogui.click(500, 1065)
    time.sleep(0.5)

    print("[*] Вставляем настроенный промпт через буфер обмена...")
    pyperclip.copy(prompt)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(1)

    print("[*] Отправляем запрос на генерацию (Ctrl + Enter)...")
    pyautogui.hotkey('ctrl', 'enter')
    print("[OK] Запрос успешно отправлен! Модель генерирует спрайтшит...")

    print("[*] Ожидаем завершения генерации (мониторинг экрана)...")
    time.sleep(15)

    # Capture result
    raw_sheet_path = "assets/monsters/goblin_raw_sheet.png"
    os.makedirs(os.path.dirname(raw_sheet_path), exist_ok=True)
    
    # Take screenshot of screen
    shot = pyautogui.screenshot()
    shot.save(raw_sheet_path)
    print(f"[OK] Снимок экрана сохранен: {raw_sheet_path}")

    print("[*] Запускаем автоматическую нарезку спрайтшита на кадры...")
    try:
        preview = slice_spritesheet(raw_sheet_path, num_frames=6, output_dir="assets/monsters/goblin_idle")
        print(f"[OK] ВСЁ ГОТОВО! Интерактивный предпросмотр: {preview}")
    except Exception as e:
        print(f"[!] Ошибка при нарезке: {e}")

    print("=" * 65)

if __name__ == "__main__":
    run_automation()
