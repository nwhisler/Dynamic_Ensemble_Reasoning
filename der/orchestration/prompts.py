import os
from pathlib import Path
from typing import Dict, Any, List

PROMPT_FILES = {
    "architect": "architect.txt",
    "implementer": "implementer.txt",
    "chairman": "chairman.txt",
    "overview": "overview.txt",
    "rules": "rules.txt"
}

def load_prompts(state: Dict[str, Any]) -> Dict[str, Any]:

    print("------------------------------------------------------------------------")
    print("-------------------------Loading-Prompts--------------------------------")
    print("------------------------------------------------------------------------")

    prompts_root = Path.cwd()
    prompts_directory = prompts_root / "prompts"
    prompts_directory.mkdir(parents=True, exist_ok=True)

    prompts: Dict[str, str] = {}

    for key, filename in PROMPT_FILES.items():
        file_path = prompts_directory / filename
        try:
            prompts[key] = file_path.read_text(encoding="utf-8")
        except Exception:
            pass

    return {"prompts": prompts}