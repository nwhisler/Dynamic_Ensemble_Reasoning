import os
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any

def is_within_base(file_path: Path, base_dir: Path) -> bool:
    
    try:
        path = Path(file_path).resolve()
        directory = Path(base_dir).resolve()

        path_ = os.path.abspath(str(path))
        directory_ = os.path.abspath(str(directory))

        if os.name == "nt":
            path_ = os.path.normcase(path_)
            directory_ = os.path.normcase(directory_)

        return os.path.commonpath([path_, directory_]) == directory_
    
    except Exception:
        return False

def load_output(output: str) -> Dict[str, Any] | None:
    
    if not isinstance(output, str):
        return None

    string = output.strip()

    try:
        json_object = json.loads(string)
        if isinstance(json_object, dict):
            return json_object
    except Exception:
        pass

    if string.startswith("```"):
        lines = string.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        fenced = "\n".join(lines).strip()
        try:
            json_object = json.loads(fenced)
            if isinstance(json_object, dict):
                return json_object
        except Exception:
            pass

    start = string.find("{")
    if start == -1:
        return None

    depth = 0
    in_str = False
    esc = False
    obj_start = None

    for idx in range(start, len(string)):
        char = string[idx]

        if in_str:
            if esc:
                esc = False
            elif char == "\\":
                esc = True
            elif char == '"':
                in_str = False
            continue

        if char == '"':
            in_str = True
            continue

        if char == "{":
            if depth == 0:
                obj_start = idx
            depth += 1
            continue

        if char == "}":
            depth -= 1
            if depth == 0 and obj_start is not None:
                candidate = string[obj_start:idx + 1]
                try:
                    obj = json.loads(candidate)
                    if isinstance(obj, dict):
                        return obj
                except Exception:
                    obj_start = None
                    continue

    return None