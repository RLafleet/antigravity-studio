import json
import os
from pathlib import Path
from typing import Dict, Any, List
from gemini_client import GeminiClient

IGNORE_DIRS = {
    ".git", ".svn", "node_modules", "vendor", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".nuxt", ".turbo", ".idea", ".vscode", "target", "storage"
}

IGNORE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".zip", ".tar", ".gz",
    ".rar", ".pdf", ".exe", ".dll", ".so", ".dylib", ".mp4", ".webp", ".lock"
}

PLAYBOOKS_FILE = Path(__file__).parent / "playbooks.json"


def get_playbooks() -> List[Dict[str, Any]]:
    """Loads playbooks from playbooks.json or returns empty list."""
    if PLAYBOOKS_FILE.exists():
        try:
            with open(PLAYBOOKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


PLAYBOOKS = get_playbooks()


def scan_workspace(workspace_path: str, max_files: int = 150) -> Dict[str, Any]:
    """Scans workspace directory to create technical snapshot for the Tech Lead."""
    root = Path(workspace_path)
    if not root.exists() or not root.is_dir():
        return {
            "exists": False,
            "path": workspace_path,
            "tree": [],
            "stack": "Unknown",
            "configs": {}
        }

    tree_entries: List[str] = []
    detected_stack: List[str] = []
    configs: Dict[str, str] = {}

    count = 0
    try:
        for p in root.rglob("*"):
            if count >= max_files:
                tree_entries.append("... [truncated remaining files]")
                break

            parts = p.relative_to(root).parts
            if any(part in IGNORE_DIRS for part in parts):
                continue
            if p.suffix.lower() in IGNORE_EXTENSIONS:
                continue

            rel_str = str(p.relative_to(root)).replace("\\", "/")
            if p.is_dir():
                tree_entries.append(f"{rel_str}/")
            else:
                tree_entries.append(rel_str)
                count += 1

                fname = p.name.lower()
                if fname == "package.json" and "package.json" not in configs:
                    detected_stack.append("Node.js/TypeScript")
                    try:
                        configs["package.json"] = p.read_text(encoding="utf-8", errors="ignore")[:1000]
                    except Exception:
                        pass
                elif fname == "pubspec.yaml" and "pubspec.yaml" not in configs:
                    detected_stack.append("Flutter/Dart")
                    try:
                        configs["pubspec.yaml"] = p.read_text(encoding="utf-8", errors="ignore")[:1000]
                    except Exception:
                        pass
                elif fname in ("pyproject.toml", "requirements.txt") and fname not in configs:
                    detected_stack.append("Python")
                    try:
                        configs[fname] = p.read_text(encoding="utf-8", errors="ignore")[:800]
                    except Exception:
                        pass
                elif fname == "cargo.toml":
                    detected_stack.append("Rust")
                elif fname == "go.mod":
                    detected_stack.append("Go")
    except Exception as e:
        tree_entries.append(f"Scan error: {str(e)}")

    return {
        "exists": True,
        "path": str(root),
        "tree": tree_entries,
        "stack": ", ".join(set(detected_stack)) if detected_stack else "Polyglot / Generic",
        "configs": configs
    }


def auto_determine_model_and_thinking(user_prompt: str, stack: str = "") -> Dict[str, str]:
    """Determines model and reasoning level based on prompt complexity."""
    p_lower = user_prompt.lower()

    complex_triggers = [
        "приложение", "сервер", "архитектур", "ui", "дизайн", "фронтенд", "бэкенд",
        "fullstack", "рефакторинг", "база данных", "api", "виджет", "создай", "разработай"
    ]
    light_triggers = ["поправь опечатку", "переименуй", "комментарий", "подправь", "print"]

    if any(k in p_lower for k in complex_triggers):
        return {
            "model": "gemini-3.8-flash",
            "thinking": "high",
            "reason": "Комплексная инженерная задача: выбран Gemini 3.8 Flash (High Reasoning)"
        }
    elif any(k in p_lower for k in light_triggers):
        return {
            "model": "gemini-3.8-flash",
            "thinking": "low",
            "reason": "Точечная правка: выбран Gemini 3.8 Flash (Low Reasoning)"
        }
    else:
        return {
            "model": "gemini-3.8-flash",
            "thinking": "medium",
            "reason": "Стандартная задача: выбран Gemini 3.8 Flash (Medium Reasoning)"
        }


TECH_LEAD_SYSTEM_PROMPT = """You are an Elite Principal AI Architect and Tech Lead orchestrating autonomous coding tasks for Google Antigravity.

Your job:
1. The user will provide a casual or concise instruction in Russian.
2. Inspect the provided workspace file tree and project context.
3. Architect the request into a high-precision, production-grade technical specification in ENGLISH for the Antigravity agent.

WHY ENGLISH?
- Token compression: Cyrillic consumes ~2.3-3 tokens/word, English consumes ~1.2 tokens/word. English saves 50-60% tokens right away!
- Precision: Coding agents reason significantly better and hallucinate less with standardized English technical terms.

WHY TARGET SCOPING?
- Without explicit file paths, agents run broad recursive scans burning 40,000+ context tokens.

OUTPUT MUST BE STRICT VALID JSON MATCHING THIS SCHEMA:
{
  "title": "Clear Technical Title in English",
  "title_ru": "Краткое название задачи на русском",
  "objective": "One-sentence high-impact objective in English",
  "target_files_to_modify": ["src/path1.ts", ...],
  "target_files_to_create": ["src/path2.ts", ...],
  "constraints_and_guardrails": [
    "Do not break backwards compatibility",
    "Preserve existing architecture and coding patterns"
  ],
  "implementation_steps": [
    "Step 1: ...",
    "Step 2: ...",
    "Step 3: ..."
  ],
  "verification_commands": [
    "npm test" or "flutter test" or test command
  ],
  "acceptance_criteria": [
    "Criterion 1: ...",
    "Criterion 2: ..."
  ],
  "antigravity_prompt": "Complete, perfectly formatted multi-line English prompt to send directly to the Antigravity agent",
  "token_savings_analysis": {
    "language_compression_pct": 55,
    "exploration_tokens_saved": 45000,
    "total_estimated_tokens_saved": 60000,
    "summary_ru": "Экономия за счет перевода на английский и точечной локализации файлов"
  }
}
"""


async def _architect_via_agy(input_payload: str, model_name: str = "gemini-3.8-flash") -> Dict[str, Any]:
    """Fallback generator using Antigravity CLI."""
    import asyncio
    agy_bin = r"C:\Users\decoriko\AppData\Local\agy\bin\agy.exe"
    prompt = f"{TECH_LEAD_SYSTEM_PROMPT}\n\nStrictly return ONLY raw JSON matching the schema without markdown fences or commentary.\n\n{input_payload}"
    try:
        cmd = [agy_bin, "--model", "gemini-3.8-flash-high", "--dangerously-skip-permissions", "-p", prompt]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        raw_text = stdout.decode("utf-8", errors="replace").strip()
        
        if raw_text:
            content = raw_text
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            start_b = content.find('{')
            end_b = content.rfind('}')
            if start_b != -1 and end_b != -1 and end_b > start_b:
                content = content[start_b:end_b + 1]
            try:
                return {"ok": True, "json": json.loads(content)}
            except Exception as e:
                return {"ok": False, "error": f"JSON parse error: {str(e)}", "raw": raw_text[:300]}

        return {"ok": False, "error": f"CLI produced no output. Stderr: {stderr.decode('utf-8', errors='replace')[:200]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}



async def architect_task(
    user_prompt: str,
    workspace_path: str,
    gemini: GeminiClient
) -> Dict[str, Any]:
    """Runs the Tech Lead phase: scans repo, prompts Gemini, produces structured specification."""
    snapshot = scan_workspace(workspace_path)

    tree_str = "\n".join(snapshot.get("tree", [])[:90])
    configs_str = ""
    for k, v in snapshot.get("configs", {}).items():
        configs_str += f"\n--- {k} ---\n{v}\n"

    input_payload = f"""=== USER REQUEST (RUSSIAN) ===
{user_prompt}

=== WORKSPACE CONTEXT ===
Path: {snapshot.get("path")}
Detected Tech Stack: {snapshot.get("stack")}

File Tree Snapshot:
{tree_str if tree_str else "(Empty directory or new project)"}

Key Configuration Snippets:
{configs_str if configs_str else "(No config files found)"}
"""

    resp = await gemini.generate(
        prompt=input_payload,
        system_instruction=TECH_LEAD_SYSTEM_PROMPT,
        json_output=True,
        temperature=0.2
    )

    if not resp.get("ok"):
        fallback_resp = await _architect_via_agy(input_payload, model_name=gemini.model_name)
        if fallback_resp.get("ok"):
            f_json = fallback_resp.get("json", {})
            f_json["auto_selection"] = auto_determine_model_and_thinking(user_prompt, snapshot.get("stack", ""))
            return {
                "ok": True,
                "spec": f_json,
                "snapshot": snapshot,
                "via_engine": "antigravity_cli",
                "usage": {}
            }
        return {
            "ok": False,
            "error": resp.get("error", "Unknown Gemini error"),
            "snapshot": snapshot
        }

    spec_json = resp.get("json")
    if not spec_json:
        fallback_resp = await _architect_via_agy(input_payload, model_name=gemini.model_name)
        if fallback_resp.get("ok"):
            f_json = fallback_resp.get("json", {})
            f_json["auto_selection"] = auto_determine_model_and_thinking(user_prompt, snapshot.get("stack", ""))
            return {
                "ok": True,
                "spec": f_json,
                "snapshot": snapshot,
                "via_engine": "antigravity_cli"
            }
        return {
            "ok": False,
            "error": f"Failed to parse JSON response: {resp.get('json_error')}",
            "raw_text": resp.get("text"),
            "snapshot": snapshot
        }

    spec_json = spec_json or {}
    spec_json["auto_selection"] = auto_determine_model_and_thinking(user_prompt, snapshot.get("stack", ""))

    return {
        "ok": True,
        "spec": spec_json,
        "snapshot": snapshot,
        "usage": resp.get("usage", {})
    }
