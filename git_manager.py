import asyncio
import os
from pathlib import Path
from typing import Dict, Any, List, Optional


async def run_git_cmd(args: List[str], cwd: str) -> Dict[str, Any]:
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", *args,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        out = stdout.decode("utf-8", errors="ignore").strip()
        err = stderr.decode("utf-8", errors="ignore").strip()
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": out,
            "stderr": err
        }
    except Exception as e:
        return {"ok": False, "returncode": -1, "stdout": "", "stderr": str(e)}


async def get_git_status(workspace_path: str) -> Dict[str, Any]:
    """Retrieves full git status for workspace."""
    if not (Path(workspace_path) / ".git").exists():
        return {
            "is_repo": False,
            "branch": "",
            "changed_files": [],
            "diff_stat": "",
            "remote": ""
        }

    branch_res = await run_git_cmd(["branch", "--show-current"], workspace_path)
    branch = branch_res["stdout"] or "main"

    remote_res = await run_git_cmd(["remote", "-v"], workspace_path)
    remote = ""
    if remote_res["ok"] and remote_res["stdout"]:
        for line in remote_res["stdout"].splitlines():
            if "(push)" in line:
                remote = line.split()[1]
                break

    status_res = await run_git_cmd(["status", "--short"], workspace_path)
    changed_files = [line.strip() for line in status_res["stdout"].splitlines() if line.strip()]

    diff_res = await run_git_cmd(["diff", "--stat"], workspace_path)
    diff_stat = diff_res["stdout"]

    last_commit_res = await run_git_cmd(["log", "-1", "--oneline"], workspace_path)
    last_commit = last_commit_res["stdout"] if last_commit_res["ok"] else ""

    return {
        "is_repo": True,
        "branch": branch,
        "remote": remote,
        "changed_files": changed_files,
        "changed_count": len(changed_files),
        "diff_stat": diff_stat,
        "last_commit": last_commit
    }


async def git_commit_and_push(workspace_path: str, message: str, push: bool = True) -> Dict[str, Any]:
    """Stages all changes, creates commit, and optionally pushes to remote."""
    if not (Path(workspace_path) / ".git").exists():
        return {"ok": False, "error": "Директория не является Git-репозиторием."}

    # git add .
    add_res = await run_git_cmd(["add", "-A"], workspace_path)
    if not add_res["ok"]:
        return {"ok": False, "error": f"Ошибка git add: {add_res['stderr']}"}

    # git commit -m message
    commit_res = await run_git_cmd(["commit", "-m", message], workspace_path)
    if not commit_res["ok"] and "nothing to commit" not in commit_res["stderr"] and "nothing to commit" not in commit_res["stdout"]:
        return {"ok": False, "error": f"Ошибка commit: {commit_res['stderr']}"}

    if not push:
        return {"ok": True, "message": "Коммит успешно создан локально.", "commit_output": commit_res["stdout"]}

    # git push
    push_res = await run_git_cmd(["push", "origin", "HEAD"], workspace_path)
    if push_res["ok"]:
        return {
            "ok": True,
            "message": "Изменения успешно закоммичены и запушены на GitHub!",
            "push_output": push_res["stdout"]
        }
    else:
        return {
            "ok": False,
            "error": f"Коммит создан, но ошибка при push в GitHub: {push_res['stderr']}",
            "partial": True
        }
