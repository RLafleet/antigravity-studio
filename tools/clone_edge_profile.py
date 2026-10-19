import os
import shutil
import time
import psutil

def is_edge_running():
    for p in psutil.process_iter(['name']):
        if p.info['name'] and 'msedge' in p.info['name'].lower():
            return True
    return False

def clone_profile():
    src_user_data = os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data')
    src_profile = os.path.join(src_user_data, 'Profile 1')
    dst_user_data = os.path.expanduser(r'~/.antigravity_studio/edge_ai_profile')
    dst_profile = os.path.join(dst_user_data, 'Default')

    print("=" * 60)
    print(" [*] Клонирование активной PRO-сессии Microsoft Edge...")
    print("=" * 60)

    if is_edge_running():
        print("[!] Microsoft Edge всё ещё запущен. Пожалуйста, закройте окна Edge на 5 секунд.")
        print("[*] Ожидаем закрытия Edge...")
        while is_edge_running():
            time.sleep(1)
        print("[OK] Edge закрыт! Начинаем мгновенное копирование сессии...")

    os.makedirs(dst_user_data, exist_ok=True)
    os.makedirs(dst_profile, exist_ok=True)

    # 1. Copy Local State (contains DPAPI decryption key for cookies)
    src_local_state = os.path.join(src_user_data, 'Local State')
    dst_local_state = os.path.join(dst_user_data, 'Local State')
    if os.path.exists(src_local_state):
        shutil.copy2(src_local_state, dst_local_state)
        print("[OK] Скопирован Local State")

    # 2. Copy Profile 1 data into Default
    items_to_copy = [
        'Cookies', 'Network', 'Preferences', 'Secure Preferences',
        'Storage', 'IndexedDB', 'Local Storage', 'Session Storage', 'Sessions'
    ]

    for item in items_to_copy:
        s = os.path.join(src_profile, item)
        d = os.path.join(dst_profile, item)
        try:
            if os.path.isfile(s):
                shutil.copy2(s, d)
                print(f"[OK] Скопирован файл: {item}")
            elif os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
                print(f"[OK] Скопирована папка: {item}")
        except Exception as e:
            print(f"[!] Пропуск {item}: {e}")

    print("=" * 60)
    print("[✓] УСПЕХ! Авторизованная PRO-сессия перенесена в профиль бота!")
    print("    Теперь вы можете снова открыть свой Edge как обычно.")
    print("    Бот теперь полностью автономен и сохранил ваш PRO-доступ.")
    print("=" * 60)

if __name__ == "__main__":
    clone_profile()
