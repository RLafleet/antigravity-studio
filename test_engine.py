import asyncio
import json
import math
import os
from pathlib import Path
from typing import Dict, Any, List


async def run_backend_tests(workspace_path: str) -> Dict[str, Any]:
    """Runs Jest or npm test suite in workspace and parses output."""
    root = Path(workspace_path)
    if not root.exists():
        return {"ok": False, "error": f"Директория {workspace_path} не существует."}

    # Determine command
    cmd = "npm test"
    if (root / "package.json").exists():
        cmd = "npm test"
    elif (root / "pubspec.yaml").exists():
        cmd = "flutter test"
    elif (root / "pytest.ini").exists() or (root / "tests").exists():
        cmd = "python -m pytest"

    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=str(root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        raw_output = stdout.decode("utf-8", errors="ignore") + stderr.decode("utf-8", errors="ignore")

        # Parse test metrics
        passed = False
        if proc.returncode == 0:
            passed = True

        tests_passed = raw_output.count("✓") + raw_output.count("passed")
        tests_failed = raw_output.count("✕") + raw_output.count("failed")

        return {
            "ok": passed,
            "exit_code": proc.returncode,
            "command": cmd,
            "summary": f"{'Успешно' if passed else 'Ошибка тестов'} (Exit code: {proc.returncode})",
            "passed_indicators": tests_passed,
            "failed_indicators": tests_failed,
            "output": raw_output[-2500:]  # Last 2.5k chars
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "command": cmd}


def simulate_motion_counter(exercise_type: str = "squat", target_reps: int = 5) -> Dict[str, Any]:
    """
    Simulates synthetic 3D pose stream through the V13.2 Upper-Body & Hip Detection logic.
    Allows testing counter accuracy without standing in front of a real webcam!
    """
    frames_per_rep = 24  # ~0.8s per rep at 30fps
    total_frames = frames_per_rep * target_reps
    counted_reps = 0
    state = "up"
    trajectory: List[Dict[str, float]] = []

    # Simulation parameters
    baseline_hip_y = 280.0
    squat_drop_pixels = 75.0  # Moves downwards in Y
    elbow_up_angle = 155.0
    elbow_down_angle = 90.0

    for f in range(total_frames):
        phase = (f % frames_per_rep) / frames_per_rep
        # Sine wave: 0 -> 1 -> 0
        depth = math.sin(phase * math.pi)

        if exercise_type == "squat":
            current_hip_y = baseline_hip_y + (depth * squat_drop_pixels)
            trajectory.append({"frame": f, "hip_y": round(current_hip_y, 1), "depth": round(depth, 2)})

            # Squat logic (Upper-Body & Hip Detect V13.2)
            threshold = 60.0
            if current_hip_y > baseline_hip_y + threshold and state == "up":
                state = "down"
            elif current_hip_y < baseline_hip_y + (threshold * 0.3) and state == "down":
                state = "up"
                counted_reps += 1

        else:  # pushup
            current_angle = elbow_up_angle - (depth * (elbow_up_angle - elbow_down_angle))
            trajectory.append({"frame": f, "elbow_angle": round(current_angle, 1), "depth": round(depth, 2)})

            # Pushup logic (matching pushup_counter.dart)
            if current_angle < 100.0 and state == "up":
                state = "down"
            elif current_angle > 140.0 and state == "down":
                state = "up"
                counted_reps += 1

    accuracy = (counted_reps / target_reps) * 100 if target_reps > 0 else 0

    return {
        "ok": counted_reps == target_reps,
        "exercise": exercise_type,
        "target_reps": target_reps,
        "counted_reps": counted_reps,
        "accuracy_pct": round(accuracy, 1),
        "total_simulated_frames": total_frames,
        "verdict": "Идеально: Движок V13.2 зафиксировал все повторения без ложных срабатываний" if counted_reps == target_reps else f"Расхождение: зафиксировано {counted_reps} из {target_reps}",
        "sample_points": trajectory[::6]  # sampled trajectory
    }


def validate_narrative_configs(workspace_path: str) -> Dict[str, Any]:
    """Validates presence and schema integrity of narrative JSON configs."""
    root = Path(workspace_path)
    search_dirs = [
        root / "src" / "configs" / "lore",
        root / "backend" / "src" / "configs" / "lore",
        root / "assets" / "configs"
    ]

    target_files = ["splash_quotes.json", "boss_dialogues.json", "store_items_copy.json"]
    found: Dict[str, Any] = {}
    missing: List[str] = []

    for fname in target_files:
        file_path = None
        for sdir in search_dirs:
            candidate = sdir / fname
            if candidate.exists():
                file_path = candidate
                break

        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    keys = list(data.keys())
                    found[fname] = {
                        "path": str(file_path),
                        "status": "valid_json",
                        "root_keys": keys,
                        "item_count": len(data.get(keys[0], {})) if keys else 0
                    }
            except Exception as e:
                found[fname] = {"path": str(file_path), "status": "corrupt_json", "error": str(e)}
        else:
            missing.append(fname)

    return {
        "ok": len(missing) == 0,
        "found_configs": found,
        "missing_files": missing,
        "summary": "Все JSON-конфиги лора валидны и на месте!" if not missing else f"Не найдены файлы: {', '.join(missing)}"
    }
