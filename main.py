import os
import sys
import time
import threading
import socket
import urllib.request
import webbrowser
from pathlib import Path

import uvicorn
from fastapi.staticfiles import StaticFiles

from server import app


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def wait_for_server(url: str, timeout: float = 12.0) -> bool:
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(f"{url}/api/config", timeout=0.8) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.15)
    return False


def start_server(port: int):
    static_dir = Path(__file__).parent / "web"
    try:
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
    except Exception:
        pass
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def main():
    print("=" * 60)
    print(" 🚀 Antigravity Studio Desktop Starting...")
    print("=" * 60)

    port = 48123
    server_url = f"http://127.0.0.1:{port}"

    already_running = False
    if is_port_in_use(port):
        if wait_for_server(server_url, timeout=1.5):
            print(f"[*] Reusing existing instance at {server_url}")
            already_running = True

    if not already_running:
        server_thread = threading.Thread(target=start_server, args=(port,), daemon=True)
        server_thread.start()

        print("[*] Waiting for API server to become ready...")
        ready = wait_for_server(server_url, timeout=12.0)
        if ready:
            print(f"[*] Antigravity Studio ready at: {server_url}")
        else:
            print(f"[!] Warning: Server did not respond within timeout, proceeding...")

    if "--browser" in sys.argv or "--web" in sys.argv:
        print(f"[*] Opening in browser: {server_url}")
        webbrowser.open(server_url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down.")
            sys.exit(0)

    try:
        import webview
        print("[*] Spawning native desktop window via WebView2...")
        window = webview.create_window(
            title="Antigravity Studio",
            url=server_url,
            width=1240,
            height=820,
            min_size=(960, 640),
            background_color="#0b0f19",
            easy_drag=True
        )
        webview.start()
    except Exception as e:
        print(f"[!] PyWebView window could not start ({e}). Launching browser...")
        webbrowser.open(server_url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down.")
            sys.exit(0)


if __name__ == "__main__":
    main()
