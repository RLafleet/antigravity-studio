import os
import sys
import time
import shutil
import subprocess
import psutil

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def is_edge_running():
    for p in psutil.process_iter(['name']):
        if p.info['name'] and 'msedge' in p.info['name'].lower():
            return True
    return False

def clone_and_restart():
    src_user_data = os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data')
    src_profile = os.path.join(src_user_data, 'Profile 1')
    dst_user_data = os.path.expanduser(r'~/.antigravity_studio/edge_ai_profile')
    dst_profile = os.path.join(dst_user_data, 'Default')

    print("[1/4] Мягкое закрытие Edge для снятия блокировки базы данных...")
    subprocess.run(["taskkill", "/IM", "msedge.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    if is_edge_running():
        subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)

    print("[2/4] Копирование сессии Google AI Studio PRO в профиль бота...")
    os.makedirs(dst_user_data, exist_ok=True)
    os.makedirs(dst_profile, exist_ok=True)

    # 1. Local State
    src_local_state = os.path.join(src_user_data, 'Local State')
    dst_local_state = os.path.join(dst_user_data, 'Local State')
    if os.path.exists(src_local_state):
        shutil.copy2(src_local_state, dst_local_state)
        print("  -> Скопирован Local State")

    # 2. Key profile folders and files
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
                print(f"  -> Файл {item} скопирован")
            elif os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
                print(f"  -> Папка {item} скопирована")
        except Exception as e:
            print(f"  -> Пропуск {item}: {e}")

    print("[3/4] Мгновенный перезапуск Microsoft Edge для пользователя...")
    # Relaunch user's Edge so their work continues seamlessly
    edge_bin = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if os.path.exists(edge_bin):
        subprocess.Popen([edge_bin, "--restore-last-session"])
        print("  -> Microsoft Edge перезапущен с восстановлением вкладок!")

    print("[4/4] Готово! Профиль бота ~/.antigravity_studio/edge_ai_profile полностью инициализирован.")

if __name__ == "__main__":
    clone_and_restart()
