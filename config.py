import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

APP_DIR = Path.home() / ".antigravity_studio"
CONFIG_FILE = APP_DIR / "config.json"
HISTORY_FILE = APP_DIR / "task_history.json"

LEGACY_APP_DIR = Path.home() / ".agy_orchestrator"
LEGACY_CONFIG_FILE = LEGACY_APP_DIR / "config.json"
LEGACY_HISTORY_FILE = LEGACY_APP_DIR / "task_history.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
    "orchestrator_model": "gemini-3.8-flash",
    "thinking_level": "high",  # 'high', 'medium', 'low', 'off'
    "default_workspace": str(Path.home() / ".gemini" / "antigravity" / "scratch" / "fitness_clicker"),
    "recent_workspaces": [
        str(Path.home() / ".gemini" / "antigravity" / "scratch" / "fitness_clicker"),
        str(Path.home() / ".gemini" / "antigravity" / "scratch" / "backend")
    ],
    "auto_approve_permissions": True,
    "language_output": "ru",
    "agy_executable": r"C:\Users\decoriko\AppData\Local\agy\bin\agy.exe",
    "execution_mode": "auto",  # 'sdk', 'cli', 'auto'
    "antigravity_data_dir": str(Path.home() / ".gemini" / "antigravity"),
    "max_steps": 30,
    "temperature": 0.2,
    "github_username": "RLafleet"
}


def ensure_app_dirs():
    APP_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> Dict[str, Any]:
    ensure_app_dirs()
    if not CONFIG_FILE.exists():
        # Migrate legacy config if present
        if LEGACY_CONFIG_FILE.exists():
            try:
                with open(LEGACY_CONFIG_FILE, "r", encoding="utf-8") as f:
                    legacy_cfg = json.load(f)
                    merged = DEFAULT_CONFIG.copy()
                    merged.update(legacy_cfg)
                    save_config(merged)
                    return merged
            except Exception:
                pass
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            merged = DEFAULT_CONFIG.copy()
            merged.update(cfg)
            return merged
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(cfg: Dict[str, Any]) -> bool:
    ensure_app_dirs()
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False


def load_history() -> List[Dict[str, Any]]:
    ensure_app_dirs()
    if not HISTORY_FILE.exists():
        if LEGACY_HISTORY_FILE.exists():
            try:
                with open(LEGACY_HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def upsert_task_history(task_entry: Dict[str, Any]):
    """Inserts or updates task in history."""
    ensure_app_dirs()
    history = load_history()
    task_id = task_entry.get("id")

    updated = False
    if task_id:
        for idx, item in enumerate(history):
            if item.get("id") == task_id:
                history[idx].update(task_entry)
                updated = True
                break

    if not updated:
        history.insert(0, task_entry)

    # Keep last 150 tasks
    history = history[:150]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving history: {e}")


def get_task_by_id(task_id: str) -> Optional[Dict[str, Any]]:
    history = load_history()
    for item in history:
        if item.get("id") == task_id:
            return item
    return None
