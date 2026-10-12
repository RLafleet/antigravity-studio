import asyncio
import os
import json
from pathlib import Path
from typing import Dict, Any, AsyncGenerator, Optional, List
from config import load_config


class WorkerEvent:
    def __init__(self, event_type: str, data: Dict[str, Any]):
        self.event_type = event_type
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
        return {"event": self.event_type, **self.data}


class WorkerEngine:
    """Manages execution of Antigravity tasks via CLI or SDK with real-time event streaming."""

    def __init__(self, workspace_path: str, model_name: Optional[str] = None, thinking_level: Optional[str] = None):
        self.workspace_path = workspace_path
        self.cfg = load_config()
        self.model_name = model_name or self.cfg.get("orchestrator_model", "gemini-3.8-flash")
        self.thinking_level = thinking_level or self.cfg.get("thinking_level", "high")
        self.is_running = False
        self._current_process: Optional[asyncio.subprocess.Process] = None

    async def execute_task(
        self,
        antigravity_prompt: str,
        verification_commands: Optional[List[str]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        self.is_running = True
        yield WorkerEvent("status", {
            "status": "starting",
            "message": "Инициализация агента Antigravity..."
        }).to_dict()

        has_sdk = False
        try:
            import google.antigravity
            has_sdk = True
        except ImportError:
            has_sdk = False

        exec_mode = self.cfg.get("execution_mode", "auto")

        if exec_mode == "sdk" and has_sdk:
            async for ev in self._run_via_sdk(antigravity_prompt):
                yield ev
        else:
            async for ev in self._run_via_cli(antigravity_prompt):
                yield ev

        # Verification step
        if verification_commands:
            yield WorkerEvent("status", {
                "status": "verifying",
                "message": "Запуск тестов и верификации..."
            }).to_dict()
            for cmd in verification_commands:
                yield WorkerEvent("verification", {"command": cmd, "status": "running"}).to_dict()
                try:
                    proc = await asyncio.create_subprocess_shell(
                        cmd,
                        cwd=self.workspace_path,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await proc.communicate()
                    out_text = stdout.decode("utf-8", errors="ignore") + stderr.decode("utf-8", errors="ignore")
                    yield WorkerEvent("verification", {
                        "command": cmd,
                        "status": "passed" if proc.returncode == 0 else "failed",
                        "output": out_text[:600]
                    }).to_dict()
                except Exception as e:
                    yield WorkerEvent("verification", {
                        "command": cmd,
                        "status": "error",
                        "output": str(e)
                    }).to_dict()

        diff_summary = await self._get_git_changes()

        created_files = []
        has_index_html = False
        try:
            for root_d, _, files in os.walk(self.workspace_path):
                if any(x in root_d for x in [".git", "node_modules", ".venv", "__pycache__", "build", "dist"]):
                    continue
                for f in files:
                    rel = os.path.relpath(os.path.join(root_d, f), self.workspace_path).replace("\\", "/")
                    created_files.append(rel)
                    if rel.lower() == "index.html":
                        has_index_html = True
        except Exception:
            pass

        yield WorkerEvent("completed", {
            "status": "completed",
            "message": "Задача успешно завершена!",
            "git_changes": diff_summary,
            "workspace_path": self.workspace_path,
            "has_index_html": has_index_html,
            "files": created_files[:25]
        }).to_dict()

        self.is_running = False

    async def _run_via_sdk(self, prompt: str) -> AsyncGenerator[Dict[str, Any], None]:
        try:
            import google.antigravity as ga
            from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig

            yield WorkerEvent("status", {
                "status": "running",
                "engine": "sdk",
                "model": self.model_name,
                "message": f"Запущен агент через Python SDK ({self.model_name})"
            }).to_dict()

            model_target = ga.models.ModelTarget(name=self.model_name)
            config = LocalAgentConfig(
                capabilities=CapabilitiesConfig(),
                model=model_target,
                system_instructions="You are an autonomous engineering agent working in workspace: " + self.workspace_path
            )

            async with Agent(config) as agent:
                response = await agent.chat(prompt)
                async for token in response:
                    yield WorkerEvent("token", {"token": token}).to_dict()

        except Exception as e:
            yield WorkerEvent("error", {
                "engine": "sdk",
                "error": f"Ошибка SDK: {str(e)}. Переключаемся на CLI..."
            }).to_dict()
            async for ev in self._run_via_cli(prompt):
                yield ev

    async def _run_via_cli(self, prompt: str) -> AsyncGenerator[Dict[str, Any], None]:
        agy_bin = self.cfg.get("agy_executable", r"C:\Users\decoriko\AppData\Local\agy\bin\agy.exe")
        if not os.path.exists(agy_bin):
            agy_bin = "agy"

        cmd = [
            agy_bin,
            "-p", prompt,
            "--dangerously-skip-permissions",
            "--add-dir", self.workspace_path
        ]

        yield WorkerEvent("status", {
            "status": "running",
            "engine": "cli",
            "model": self.model_name,
            "message": f"Запуск Antigravity CLI ({self.model_name}) в {self.workspace_path}..."
        }).to_dict()

        try:
            self._current_process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.workspace_path,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            brain_dir = Path.home() / ".gemini" / "antigravity-cli" / "brain"
            lines_read = 0
            log_file: Optional[Path] = None
            finished_seen = False

            while self.is_running and self._current_process.returncode is None:
                if not log_file or not log_file.exists():
                    if brain_dir.exists():
                        dirs = sorted(brain_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
                        if dirs:
                            candidate = dirs[0] / ".system_generated" / "logs" / "transcript.jsonl"
                            if candidate.exists():
                                log_file = candidate

                if log_file and log_file.exists():
                    try:
                        with open(log_file, "r", encoding="utf-8") as f:
                            all_lines = f.readlines()
                            if len(all_lines) > lines_read:
                                for line in all_lines[lines_read:]:
                                    lines_read += 1
                                    try:
                                        obj = json.loads(line)
                                        if obj.get("thinking"):
                                            yield WorkerEvent("thought", {"thought": obj.get("thinking")}).to_dict()
                                        if obj.get("tool_calls"):
                                            for tc in obj.get("tool_calls", []):
                                                yield WorkerEvent("tool", {
                                                    "tool": f"Tool: {tc.get('name')}({tc.get('args', {})})"
                                                }).to_dict()
                                        if obj.get("type") == "PLANNER_RESPONSE" and obj.get("content"):
                                            yield WorkerEvent("token", {"token": obj.get("content")}).to_dict()
                                            finished_seen = True
                                    except Exception:
                                        pass
                    except Exception:
                        pass

                if finished_seen:
                    await asyncio.sleep(1.5)
                    break

                try:
                    await asyncio.wait_for(asyncio.shield(self._current_process.wait()), timeout=0.8)
                except asyncio.TimeoutError:
                    pass

            if self._current_process.returncode is None:
                try:
                    self._current_process.terminate()
                except Exception:
                    pass

            # Final check of lines
            if log_file and log_file.exists():
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        all_lines = f.readlines()
                        if len(all_lines) > lines_read:
                            for line in all_lines[lines_read:]:
                                lines_read += 1
                                try:
                                    obj = json.loads(line)
                                    if obj.get("thinking"):
                                        yield WorkerEvent("thought", {"thought": obj.get("thinking")}).to_dict()
                                    if obj.get("tool_calls"):
                                        for tc in obj.get("tool_calls", []):
                                            yield WorkerEvent("tool", {
                                                "tool": f"Tool: {tc.get('name')}({tc.get('args', {})})"
                                            }).to_dict()
                                    if obj.get("type") == "PLANNER_RESPONSE" and obj.get("content"):
                                        yield WorkerEvent("token", {"token": obj.get("content")}).to_dict()
                                except Exception:
                                    pass
                except Exception:
                    pass

        except Exception as e:
            yield WorkerEvent("error", {
                "engine": "cli",
                "error": f"Ошибка запуска CLI: {str(e)}"
            }).to_dict()

    async def _get_git_changes(self) -> Dict[str, Any]:
        try:
            proc = await asyncio.create_subprocess_shell(
                "git status --short",
                cwd=self.workspace_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            status_text = stdout.decode("utf-8", errors="ignore").strip()
            files = [line.strip() for line in status_text.splitlines() if line.strip()]

            diff_proc = await asyncio.create_subprocess_shell(
                "git diff --stat",
                cwd=self.workspace_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            diff_out, _ = await diff_proc.communicate()

            return {
                "changed_files_count": len(files),
                "files": files[:20],
                "diff_stat": diff_out.decode("utf-8", errors="ignore").strip()
            }
        except Exception:
            return {"changed_files_count": 0, "files": [], "diff_stat": ""}

    def stop(self):
        self.is_running = False
        if self._current_process:
            try:
                self._current_process.terminate()
            except Exception:
                pass
