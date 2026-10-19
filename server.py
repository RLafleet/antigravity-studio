import asyncio
import json
import os
import sys
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import (
    load_config, save_config, load_history,
    upsert_task_history, get_task_by_id, HISTORY_FILE,
    load_day_plan, save_day_plan, DAY_PLAN_FILE
)
from gemini_client import GeminiClient
from spec_architect import (
    scan_workspace, architect_task,
    auto_determine_model_and_thinking, get_playbooks, PLAYBOOKS_FILE
)
from worker_engine import WorkerEngine
from test_engine import (
    run_backend_tests, simulate_motion_counter,
    validate_narrative_configs, run_custom_command
)
from git_manager import get_git_status, git_commit_and_push
from day_orchestrator import DayOrchestrator
from board_room import BoardRoom, load_chat_history, save_chat_history

app = FastAPI(title="Antigravity Studio API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static assets mount for monsters and previews
os.makedirs("assets", exist_ok=True)
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

@app.get("/arena")
async def get_arena():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/assets/monsters/goblin_puppet/arena.html")

@app.get("/arena3d")
async def get_arena_3d():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/assets/monsters/goblin_puppet/arena_3d.html")

@app.get("/tools/content.js")
async def get_content_js():
    from fastapi.responses import FileResponse
    return FileResponse("tools/ai_studio_extension/content.js", media_type="application/javascript")

# Sprite Bridge State
sprite_bridge_state = {
    "tab_connected": False,
    "last_ping": 0,
    "pending_task": None,
    "latest_result": None
}

active_worker: Optional[WorkerEngine] = None
board_room = BoardRoom()



active_day_orchestrator: Optional[DayOrchestrator] = None
active_day_task: Optional[asyncio.Task] = None


class ConfigModel(BaseModel):
    gemini_api_key: Optional[str] = None
    gemini_api_key_a: Optional[str] = None
    gemini_api_key_b: Optional[str] = None
    orchestrator_model: Optional[str] = None
    thinking_level: Optional[str] = None
    default_workspace: Optional[str] = None
    auto_approve_permissions: Optional[bool] = None
    execution_mode: Optional[str] = None
    agy_executable: Optional[str] = None
    github_username: Optional[str] = None
    day_cooldown_seconds: Optional[int] = None


class DayGoalRequest(BaseModel):
    goal: str
    workspace_path: Optional[str] = None


class ScanRequest(BaseModel):
    workspace_path: str


class ArchitectRequest(BaseModel):
    user_prompt: str
    workspace_path: str
    model_name: Optional[str] = None
    thinking_level: Optional[str] = None


class OpenRequest(BaseModel):
    path: Optional[str] = None
    url: Optional[str] = None


class MotionTestRequest(BaseModel):
    exercise: str = "squat"  # 'squat' or 'pushup'
    reps: int = 5


class GitCommitRequest(BaseModel):
    workspace_path: str
    message: str
    push: bool = True


class CustomCommandRequest(BaseModel):
    command: str
    workspace_path: str


class PlaybookModel(BaseModel):
    id: str
    title: str
    category: str
    description: str
    template: str


class BoardChatRequest(BaseModel):
    role: str  # "tech_lead" or "director"
    message: str


class BoardDebateRequest(BaseModel):
    topic: str
    max_rounds: int = 3


class BoardApplyRequest(BaseModel):
    role: str  # "tech_lead", "director", or "debate"



class SpriteTaskRequest(BaseModel):
    prompt: Optional[str] = None
    num_frames: Optional[int] = 6
    target: Optional[str] = "boss" # "boss", "arena_bg", "goblin_hurt", "player_fist"


class SpriteResultPayload(BaseModel):
    task_id: str
    image_base64: str


# --- Sprite Bridge Endpoints ---

@app.get("/api/bridge/status")
async def get_bridge_status():
    import time
    is_alive = (time.time() - sprite_bridge_state["last_ping"]) < 45 if sprite_bridge_state["last_ping"] else False
    return {
        "ok": True,
        "connected": is_alive,
        "has_pending_task": sprite_bridge_state["pending_task"] is not None,
        "pending_task": sprite_bridge_state["pending_task"],
        "latest_result": sprite_bridge_state["latest_result"]
    }


@app.post("/api/bridge/task")
async def create_bridge_task(req: SpriteTaskRequest):
    import time
    default_prompt = (
        "2D video game animation sprite sheet of a skinny green goblin character with droopy tired eyes, "
        "wearing a ragged brown tunic and holding pink dumbbells. "
        "Generate 6 separate frames for an idle breathing animation cycle in a single horizontal strip. "
        "IMPORTANT: Each frame must be widely spaced apart with generous empty padding between characters, "
        "so arms, weapons and ears never touch or overlap. Solid bright red background #FF0000 for easy chroma key. "
        "Feet must remain firmly planted at the exact same ground level across all 6 frames."
    )
    task_id = f"task_{int(time.time())}"
    sprite_bridge_state["pending_task"] = {
        "id": task_id,
        "prompt": req.prompt or default_prompt,
        "num_frames": req.num_frames or 6,
        "target": req.target or "boss",
        "created_at": time.time()
    }
    sprite_bridge_state["latest_result"] = None
    return {"ok": True, "task_id": task_id, "prompt": sprite_bridge_state["pending_task"]["prompt"]}


@app.get("/api/bridge/poll")
async def poll_bridge_task():
    import time
    sprite_bridge_state["last_ping"] = time.time()
    sprite_bridge_state["tab_connected"] = True
    task = sprite_bridge_state["pending_task"]
    return {"ok": True, "task": task}


@app.post("/api/bridge/clear")
async def clear_bridge_task():
    sprite_bridge_state["pending_task"] = None
    return {"ok": True}


@app.post("/api/bridge/result")
async def submit_bridge_result(payload: SpriteResultPayload):
    import time
    import base64
    from tools.slice_spritesheet import slice_spritesheet
    
    raw_b64 = payload.image_base64
    if "," in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]
    img_bytes = base64.b64decode(raw_b64)

    target = "boss"
    num_frames = 1
    if sprite_bridge_state["pending_task"]:
        target = sprite_bridge_state["pending_task"].get("target", "boss")
        num_frames = sprite_bridge_state["pending_task"].get("num_frames", 1)

    from PIL import Image
    import numpy as np

    if target == "arena_bg":
        out_path = os.path.abspath("assets/monsters/goblin_puppet/arena_bg.png")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(img_bytes)
        sprite_bridge_state["pending_task"] = None
        sprite_bridge_state["latest_result"] = {
            "task_id": payload.task_id,
            "preview_url": "/assets/monsters/goblin_puppet/arena.html",
            "image": "/assets/monsters/goblin_puppet/arena_bg.png",
            "target": "arena_bg",
            "timestamp": time.time()
        }
        return {"ok": True, "image": "/assets/monsters/goblin_puppet/arena_bg.png"}

    elif num_frames == 1 or target in ["goblin_hurt", "player_fist", "boss"]:
        raw_name = f"{target}_raw.png"
        raw_path = os.path.abspath(f"assets/monsters/goblin_puppet/{raw_name}")
        os.makedirs(os.path.dirname(raw_path), exist_ok=True)
        with open(raw_path, "wb") as f:
            f.write(img_bytes)

        # High quality alpha cutout with rembg
        try:
            from rembg import remove
            input_img = Image.open(raw_path)
            cutout_img = remove(input_img)
            # Crop to character bounding box
            arr = np.array(cutout_img)
            alpha = arr[:, :, 3]
            nonzero_y, nonzero_x = np.nonzero(alpha > 10)
            if len(nonzero_y) > 0 and len(nonzero_x) > 0:
                y_min, y_max = nonzero_y.min(), nonzero_y.max()
                x_min, x_max = nonzero_x.min(), nonzero_x.max()
                cutout_img = cutout_img.crop((x_min, y_min, x_max + 1, y_max + 1))
            
            clean_name = f"{target}.png" if target != "boss" else "goblin_boss.png"
            clean_path = os.path.abspath(f"assets/monsters/goblin_puppet/{clean_name}")
            cutout_img.save(clean_path)
            if target == "boss":
                cutout_img.save(os.path.abspath("assets/monsters/goblin_boss_clean.png"))
        except Exception as e:
            print("rembg cutout error:", e)
            img = Image.open(raw_path).convert('RGBA')
            img.save(os.path.abspath(f"assets/monsters/goblin_puppet/{target}.png"))

        sprite_bridge_state["pending_task"] = None
        sprite_bridge_state["latest_result"] = {
            "task_id": payload.task_id,
            "preview_url": "/assets/monsters/goblin_puppet/arena.html",
            "target": target,
            "timestamp": time.time()
        }
        return {"ok": True, "target": target}
    else:
        raw_path = os.path.abspath("assets/monsters/goblin_raw_sheet.png")
        os.makedirs(os.path.dirname(raw_path), exist_ok=True)
        with open(raw_path, "wb") as f:
            f.write(img_bytes)

        preview_file = slice_spritesheet(raw_path, num_frames=num_frames, output_dir="assets/monsters/goblin_idle")

        sprite_bridge_state["pending_task"] = None
        sprite_bridge_state["latest_result"] = {
            "task_id": payload.task_id,
            "preview_url": "/assets/monsters/goblin_idle/preview.html",
            "frames_dir": "/assets/monsters/goblin_idle",
            "frames_count": num_frames,
            "timestamp": time.time()
        }
        return {"ok": True, "preview": preview_file}


# --- Endpoints ---

@app.get("/api/config")
async def get_config():
    return load_config()


@app.post("/api/config")
async def update_config(data: ConfigModel):
    current = load_config()
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    current.update(update_data)
    success = save_config(current)
    return {"ok": success, "config": current}


@app.get("/api/models")
async def get_models():
    cfg = load_config()
    client = GeminiClient(
        api_key=cfg.get("gemini_api_key", ""),
        model_name=cfg.get("orchestrator_model", "gemini-3.8-flash")
    )
    return await client.get_models_catalog()


@app.post("/api/test_key")
async def test_key():
    cfg = load_config()
    client = GeminiClient(
        api_key=cfg.get("gemini_api_key", ""),
        model_name=cfg.get("orchestrator_model", "gemini-3.8-flash")
    )
    return await client.test_connection()


@app.get("/api/playbooks")
async def get_playbooks_endpoint():
    return {"ok": True, "playbooks": get_playbooks()}


@app.post("/api/playbooks")
async def save_playbooks_endpoint(req: List[Dict[str, Any]]):
    try:
        with open(PLAYBOOKS_FILE, "w", encoding="utf-8") as f:
            json.dump(req, f, indent=2, ensure_ascii=False)
        return {"ok": True, "playbooks": req}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/playbooks/add")
async def add_playbook_endpoint(item: PlaybookModel):
    current = get_playbooks()
    updated = False
    for idx, pb in enumerate(current):
        if pb.get("id") == item.id:
            current[idx] = item.dict()
            updated = True
            break
    if not updated:
        current.insert(0, item.dict())
    try:
        with open(PLAYBOOKS_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2, ensure_ascii=False)
        return {"ok": True, "playbooks": current}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.delete("/api/playbooks/{playbook_id}")
async def delete_playbook_endpoint(playbook_id: str):
    current = get_playbooks()
    filtered = [pb for pb in current if pb.get("id") != playbook_id]
    try:
        with open(PLAYBOOKS_FILE, "w", encoding="utf-8") as f:
            json.dump(filtered, f, indent=2, ensure_ascii=False)
        return {"ok": True, "playbooks": filtered}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/scan")
async def scan(req: ScanRequest):
    return scan_workspace(req.workspace_path)


@app.post("/api/select_folder")
async def select_folder():
    """Opens native Windows folder picker dialog."""
    try:
        ps_script = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "$f = New-Object System.Windows.Forms.FolderBrowserDialog; "
            "$f.Description = 'Выберите директорию проекта для Antigravity Studio'; "
            "if ($f.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $f.SelectedPath }"
        )
        proc = await asyncio.create_subprocess_exec(
            "powershell", "-NoProfile", "-Command", ps_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        selected = stdout.decode("utf-8", errors="ignore").strip()
        if selected and os.path.isdir(selected):
            cfg = load_config()
            recents = cfg.get("recent_workspaces", [])
            if selected not in recents:
                recents.insert(0, selected)
                cfg["recent_workspaces"] = recents[:10]
            cfg["default_workspace"] = selected
            save_config(cfg)
            return {"ok": True, "path": selected}
        return {"ok": False, "cancelled": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/open_folder")
async def open_folder(req: OpenRequest):
    cfg = load_config()
    p = req.path or cfg.get("default_workspace", "")
    if p:
        try:
            folder = os.path.dirname(p) if os.path.isfile(p) else p
            os.makedirs(folder, exist_ok=True)
            subprocess.Popen(["explorer.exe", os.path.abspath(folder)])
            return {"ok": True, "path": folder}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    return {"ok": False, "error": "Путь не указан"}


@app.post("/api/serve_workspace")
async def serve_workspace(req: OpenRequest):
    cfg = load_config()
    p = req.path or cfg.get("default_workspace", "")
    if not p or not os.path.isdir(p):
        return {"ok": False, "error": "Директория проекта не найдена"}

    port = 8080
    url = f"http://localhost:{port}"

    try:
        subprocess.Popen(
            [sys.executable, "-m", "http.server", str(port)],
            cwd=p,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        await asyncio.sleep(0.8)
        webbrowser.open(url)
        return {"ok": True, "url": url}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# --- Testing Studio Endpoints ---

@app.post("/api/test/backend")
async def test_backend(req: ScanRequest):
    """Executes backend test suite."""
    return await run_backend_tests(req.workspace_path)


@app.post("/api/test/motion")
async def test_motion(req: MotionTestRequest):
    """Runs synthetic pose simulator for squats or pushups."""
    return simulate_motion_counter(req.exercise, req.reps)


@app.post("/api/test/lore")
async def test_lore(req: ScanRequest):
    """Validates narrative JSON files."""
    return validate_narrative_configs(req.workspace_path)


@app.post("/api/test/custom")
async def test_custom(req: CustomCommandRequest):
    """Executes any custom test or build command."""
    return await run_custom_command(req.command, req.workspace_path)


# --- Day Plan (Slow & Steady Daemon) Endpoints ---

@app.get("/api/day_plan")
async def get_day_plan_api():
    plan = load_day_plan()
    is_running = active_day_orchestrator is not None and active_day_orchestrator.is_running
    is_paused = active_day_orchestrator is not None and active_day_orchestrator.is_paused
    return {
        "ok": True,
        "plan": plan,
        "is_running": is_running,
        "is_paused": is_paused
    }


@app.post("/api/day_plan/create")
async def create_day_plan_api(req: DayGoalRequest):
    global active_day_orchestrator
    cfg = load_config()
    ws = req.workspace_path or cfg.get("default_workspace", "")
    active_day_orchestrator = DayOrchestrator(workspace_path=ws)
    res = await active_day_orchestrator.create_plan(req.goal)
    return res


@app.post("/api/day_plan/start")
async def start_day_plan_api(req: Optional[ScanRequest] = None):
    global active_day_orchestrator, active_day_task
    cfg = load_config()
    ws = req.workspace_path if req else cfg.get("default_workspace", "")
    if not active_day_orchestrator:
        active_day_orchestrator = DayOrchestrator(workspace_path=ws)

    if not active_day_task or active_day_task.done():
        active_day_task = asyncio.create_task(active_day_orchestrator.run_pipeline())
        return {"ok": True, "message": "Конвейер дневной задачи запущен в фоне (Slow & Steady)"}
    return {"ok": True, "message": "Конвейер уже запущен"}


@app.post("/api/day_plan/pause")
async def pause_day_plan_api():
    global active_day_orchestrator
    if active_day_orchestrator:
        active_day_orchestrator.pause()
        return {"ok": True, "message": "Пауза запрошена"}
    return {"ok": False, "error": "Конвейер не активен"}


@app.post("/api/day_plan/clear")
async def clear_day_plan_api():
    global active_day_orchestrator, active_day_task
    if active_day_orchestrator:
        active_day_orchestrator.pause()
    if active_day_task and not active_day_task.done():
        active_day_task.cancel()
    if DAY_PLAN_FILE.exists():
        try:
            DAY_PLAN_FILE.unlink()
        except Exception:
            pass
    active_day_orchestrator = None
    active_day_task = None
    return {"ok": True, "message": "План на день очищен"}


# --- Board Room Endpoints ---

@app.get("/api/board/history")
async def get_board_history(role: str = "tech_lead"):
    """Returns chat history for tech_lead, director, or debate."""
    return {"ok": True, "role": role, "history": load_chat_history(role)}


@app.post("/api/board/chat")
async def board_chat(req: BoardChatRequest):
    """Sends user message to Tech Lead or Revenue Director."""
    return await board_room.talk_to_role(req.role, req.message)


@app.post("/api/board/debate")
async def board_debate(req: BoardDebateRequest):
    """Runs autonomous AI-to-AI debate between Director and Tech Lead."""
    results = []
    async for event in board_room.run_ai_debate(req.topic, req.max_rounds):
        results.append(event)
    return {"ok": True, "events": results}


@app.get("/api/board/debate/stream")
async def board_debate_stream(topic: str, max_rounds: int = 3):
    """Streams live AI-to-AI debate events via Server-Sent Events (SSE)."""
    async def event_generator():
        async for event in board_room.run_ai_debate(topic, max_rounds):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/board/stop_debate")
async def stop_board_debate():
    """Interrupts active AI debate."""
    board_room.stop_debate()
    return {"ok": True, "message": "Дебаты прерваны"}


@app.post("/api/board/apply_to_plan")
async def apply_board_to_plan(req: BoardApplyRequest):
    """Applies dialog consensus and adjustments directly to day_plan.json."""
    return await board_room.apply_dialog_to_plan(req.role)


@app.post("/api/board/clear")
async def clear_board_history(req: BoardApplyRequest):
    """Clears history for specified role."""
    save_chat_history(req.role, [])
    return {"ok": True, "message": f"История диалога ({req.role}) очищена"}


# --- Git Endpoints ---


@app.post("/api/git/status")
async def git_status(req: ScanRequest):
    """Returns git status and diff stats."""
    return await get_git_status(req.workspace_path)


@app.post("/api/git/commit")
async def git_commit(req: GitCommitRequest):
    """Commits and pushes changes."""
    return await git_commit_and_push(req.workspace_path, req.message, req.push)


# --- Architecture & Execution ---

@app.post("/api/architect")
async def generate_spec(req: ArchitectRequest):
    cfg = load_config()
    api_key = cfg.get("gemini_api_key", "")

    auto_decision = auto_determine_model_and_thinking(req.user_prompt)
    model = req.model_name
    if not model or model == "auto":
        model = auto_decision["model"]
    thinking = req.thinking_level
    if not thinking or thinking == "auto":
        thinking = auto_decision["thinking"]

    client = GeminiClient(api_key=api_key, model_name=model, thinking_level=thinking)
    result = await architect_task(req.user_prompt, req.workspace_path, client)

    if result.get("ok") and result.get("spec"):
        spec = result["spec"]
        task_id = f"task_{int(datetime.now().timestamp())}"
        spec["task_id"] = task_id
        entry = {
            "id": task_id,
            "title": spec.get("title_ru") or spec.get("title") or "Новая задача",
            "title_en": spec.get("title", ""),
            "workspace": req.workspace_path,
            "user_prompt": req.user_prompt,
            "model_name": model,
            "thinking_level": thinking,
            "status": "spec_ready",
            "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "spec": spec,
            "token_stats": spec.get("token_savings_analysis", {})
        }
        upsert_task_history(entry)

    return result


@app.get("/api/history")
async def get_history():
    return load_history()


@app.delete("/api/history/{task_id}")
async def delete_history_item(task_id: str):
    history = load_history()
    history = [t for t in history if t.get("id") != task_id]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/stop")
async def stop_execution():
    global active_worker, active_day_orchestrator
    stopped = False
    if active_worker and active_worker.is_running:
        active_worker.stop()
        stopped = True
    if active_day_orchestrator and active_day_orchestrator.is_running:
        active_day_orchestrator.pause()
        stopped = True
    if stopped:
        return {"ok": True, "message": "Остановка задачи запрошена"}
    return {"ok": False, "message": "Нет активных задач"}


@app.get("/api/worker/status")
async def get_worker_status():
    global active_worker, active_day_orchestrator, active_day_task
    cfg = load_config()
    day_running = bool(active_day_task and not active_day_task.done() and active_day_orchestrator and active_day_orchestrator.is_running)
    single_running = bool(active_worker and active_worker.is_running)

    plan_data = load_day_plan() if day_running else None
    current_step = None
    if plan_data and "steps" in plan_data:
        idx = plan_data.get("current_step_index", 0)
        if idx < len(plan_data["steps"]):
            current_step = plan_data["steps"][idx]

    is_running = single_running or day_running
    mode = "day_pipeline" if day_running else ("single_task" if single_running else "idle")
    
    task_title = None
    if day_running:
        task_title = (current_step.get("title") if current_step else plan_data.get("goal"))
    elif single_running:
        task_title = "Выполнение задания"

    model = "gemini-3.8-flash"
    thinking = "high"
    if day_running and current_step:
        model = current_step.get("model", "gemini-3.8-flash")
        thinking = current_step.get("thinking_level", "high")
    elif single_running and active_worker:
        model = active_worker.model_name
        thinking = active_worker.thinking_level

    return {
        "ok": True,
        "is_running": is_running,
        "mode": mode,
        "task_title": task_title,
        "model": model,
        "thinking": thinking,
        "step_index": plan_data.get("current_step_index") if plan_data else None,
        "total_steps": plan_data.get("total_steps") if plan_data else None,
        "workspace_path": cfg.get("default_workspace", "")
    }



@app.websocket("/ws/execute")
async def websocket_execute(websocket: WebSocket):
    global active_worker
    await websocket.accept()

    try:
        data = await websocket.receive_text()
        req = json.loads(data)

        prompt = req.get("antigravity_prompt", "")
        workspace = req.get("workspace_path", "")
        verification_cmds = req.get("verification_commands", [])
        title_ru = req.get("title_ru", "Задача")
        token_stats = req.get("token_stats", {})
        task_id = req.get("task_id") or f"task_{int(datetime.now().timestamp())}"

        cfg = load_config()
        model_name = req.get("model_name")
        thinking_level = req.get("thinking_level")

        if not model_name or model_name == "auto" or not thinking_level or thinking_level == "auto":
            auto_decision = auto_determine_model_and_thinking(prompt)
            if not model_name or model_name == "auto":
                model_name = auto_decision["model"]
            if not thinking_level or thinking_level == "auto":
                thinking_level = auto_decision["thinking"]

        model_name = model_name or cfg.get("orchestrator_model", "gemini-3.8-flash")
        thinking_level = thinking_level or cfg.get("thinking_level", "high")

        if not workspace or not os.path.isdir(workspace):
            await websocket.send_json({"event": "error", "error": f"Папка проекта не найдена: {workspace}"})
            await websocket.close()
            return

        active_worker = WorkerEngine(workspace_path=workspace, model_name=model_name, thinking_level=thinking_level)

        history_entry = {
            "id": task_id,
            "title": title_ru,
            "workspace": workspace,
            "prompt": prompt,
            "status": "running",
            "model_name": model_name,
            "thinking_level": thinking_level,
            "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "token_stats": token_stats,
            "logs": []
        }
        upsert_task_history(history_entry)

        async for event in active_worker.execute_task(prompt, verification_cmds):
            await websocket.send_json(event)
            if event.get("event") == "completed":
                history_entry["status"] = "completed"
                history_entry["git_changes"] = event.get("git_changes")
                history_entry["files"] = event.get("files", [])
                history_entry["has_index_html"] = event.get("has_index_html", False)
                history_entry["workspace_path"] = event.get("workspace_path", workspace)
            elif event.get("event") == "error":
                history_entry["status"] = "error"
                history_entry["error"] = event.get("error")

        upsert_task_history(history_entry)

    except WebSocketDisconnect:
        if active_worker:
            active_worker.stop()
    except Exception as e:
        try:
            await websocket.send_json({"event": "error", "error": str(e)})
        except Exception:
            pass
    finally:
        active_worker = None
