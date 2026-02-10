import json
import os
from typing import Dict, Any, Tuple
from pathlib import  Path

LANGUAGES = {"python", "c++", "java"}
PHASES = {"bootstrap", "iterate"}
STYLES = {"clean", "minimal", "performance"}

def collect_task_values() -> Tuple[str, str, str, str]:

    phase = str(input("\nWhat phase is this program in?\nThe supported phases are bootstrap and iterate.\n"))
    phase = phase.strip().lower() if (isinstance(phase, str) and phase.strip().lower() in PHASES) else "bootstrap"

    goal = str(input("\nWhat's the overall goal of this program?\n")).strip()

    language = str(input("\nWhat coding language should be used to compose this program?\nThe supported coding languages are python, java, c++\n"))
    language = language.strip().lower() if (isinstance(language, str) and language.strip().lower() in LANGUAGES) else "python"

    style = str(input("\nWhat style of programming do you perfer?\nThe supported styles are clean, minimal, performance\n"))
    style = style.strip().lower() if (isinstance(style, str) and style.strip().lower() in STYLES) else "clean"

    return (phase, goal, language, style)

def parse_task(memory: Dict[str, Any], task_json: Dict[str, Any]) -> Tuple[str | None, str | None, str | None, str | None]:

    exploration = memory.get("exploration")
    if not isinstance(exploration, dict):
        exploration = {}

    warmup_runs = exploration.get("warmup_runs")
    if not isinstance(warmup_runs, (int, float)) or not(0 <= int(warmup_runs) <= 3):
        warmup_runs = 3
    warmup_runs = int(warmup_runs)

    runs_completed = exploration.get("runs_completed")
    if not isinstance(runs_completed, (int, float)):
        runs_completed = 0
    runs_completed = int(runs_completed)

    phase = "iterate" if runs_completed >= warmup_runs else "bootstrap"

    goal = task_json.get("goal", None)
    goal = goal.strip() if isinstance(goal, str) else None

    language = task_json.get("language", None)
    language = language.strip().lower() if (isinstance(language, str) and language.strip().lower() in LANGUAGES) else None

    style = task_json.get("style", None)
    style = style.strip().lower() if(isinstance(style, str) and style.strip().lower() in STYLES) else None

    return (phase, goal, language, style)

def load_task(task_path: Path) -> Dict[str, Any] | None:

    task_json = None
    task_path = str(task_path)
    try:
        with open(task_path, "r", encoding="utf-8") as fh:
            task_json = json.load(fh)
    except Exception:
        task_json = None
        pass 

    return task_json

def write_task(task_path: Path, task: Dict[str, Any]) -> bool:

    if not isinstance(task, dict):
        return False

    written = False
    task_path = str(task_path)
    try:
        with open(task_path, "w", encoding="utf-8") as fh:
            json.dump(task, fh, indent=2, sort_keys=True)
        written = True
    except Exception:
        written = False
        pass

    return written

def normalize_task(state: Dict[str, Any]) -> Dict[str, Any]:

    print("------------------------------------------------------------------------")
    print("-------------------------Normalizing-Task-------------------------------")
    print("------------------------------------------------------------------------")

    task: Dict[str, str] = {}
  
    root = state.get("root")
    root = root.strip() if isinstance(root, str) else None
    if root is None:
        root = os.getcwd()
    root = Path(root).resolve()

    memory = state.get("memory")
    if not isinstance(memory, dict):
        memory = {}

    task_directory = root / "task"
    task_directory.mkdir(parents=True, exist_ok=True)

    task_path = task_directory / "task.json"

    first_run = state.get("first_run")
    if not isinstance(first_run, bool):
        if isinstance(first_run, str):
            first_run = first_run.strip().lower()
            if first_run in {"false", "0", "0.0"}:
                first_run = False
            elif first_run in {"true", "1", "1.0"}:
                first_run = True
            else:
                first_run = None
        elif isinstance(first_run, (int, float)):
            if first_run == 0 or first_run == 0.0:
                first_run = False
            elif first_run == 1 or first_run == 1.0:
                first_run = True
            else:
                first_run = None
        if first_run is None:
            if task_path.exists():
                first_run = False
            else:
                first_run = True

    if first_run:
        phase, goal, language, style = collect_task_values()
    else:
        task_json = load_task(task_path)
        if task_json is not None:
            phase, goal, language, style = parse_task(memory, task_json)
            if phase is None or goal is None or language is None or style is None:
                print("Missing information from previous run, please re-input these values:\n")
                phase, goal, language, style = collect_task_values()
        else:
            print("Previous task file could not be located, please re-input these values:\n")
            phase, goal, language, style = collect_task_values()

    task["phase"] = phase
    task["goal"] = goal
    task["language"] = language
    task["style"] = style

    written = write_task(task_path, task) 
    if not written:
        written = write_task(task_path, task) 

    return {"task": task, "root": str(root), "first_run": bool(first_run)}