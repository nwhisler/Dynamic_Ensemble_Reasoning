import ast
import json
import os
from pathlib import Path
from copy import deepcopy
from typing import Dict, Any, List, Tuple
from memory.store import repair_memory
from utils.utils import is_within_base, load_output
from .runner import run_provider

PHASES = {"bootstrap", "iterate"}

def next_run_id(last_run_id: str | None) -> str:
    
    if isinstance(last_run_id, str) and last_run_id.startswith("run_"):
        try:
            n = int(last_run_id.split("_", 1)[1])
            return f"run_{n+1:06d}"
        except Exception:
            pass
    return "run_000001"

def extract_file_paths(code_directory: Dict[str, Any]) -> List[str]:

    if not isinstance(code_directory, dict) or not code_directory:
        return []

    code_directory = dict(sorted(code_directory.items()))
    file_paths = []
    for key, value in code_directory.items():
        if key == "dirs":
            if isinstance(value, dict):
                for _, dir_ in value.items():
                    if isinstance(dir_, dict):
                        file_paths += extract_file_paths(dir_)
        elif key == "files":
            if isinstance(value, list):
                for file in value:
                    if isinstance(file, dict):
                        file_path = file.get("path")
                        file_path = file_path.strip() if isinstance(file_path, str) else ""
                        if not file_path:
                            continue
                        if file_path not in file_paths:
                            file_paths.append(file_path)

    return file_paths

def parse_priorities(priorities: Dict[str, List[str]]) -> List[str]:

    if not isinstance(priorities, dict):
        return []

    next_priorities = priorities.get("next_priorities")
    if not isinstance(next_priorities, list):
        next_priorities = []
    next_priorities = [string for string in next_priorities if isinstance(string, str)]

    return next_priorities

def chairman_overview(repaired_memory: Dict[str, Any], prompts: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:

    print("------------------------------------------------------------------------")
    print("-------------------------Chairman-Overview------------------------------")
    print("------------------------------------------------------------------------")

    if not isinstance(repaired_memory, dict) or not isinstance(prompts, dict):
        return {}

    code_review: List[Dict[str, Any]] = []

    phase = task.get("phase")
    phase = phase.strip().lower() if (isinstance(phase, str) and phase.strip().lower() in PHASES) else "bootstrap"

    rules = prompts.get("rules")
    rules = rules.strip() if isinstance(rules, str) else ""

    chairman_prompt = prompts.get("overview")
    chairman_prompt = chairman_prompt.strip() if isinstance(chairman_prompt, str) else ""

    run_id = repaired_memory.get("current_run_id")
    run_id = run_id.strip() if isinstance(run_id, str) else ""

    model_pool = repaired_memory.get("model_pool")
    if not isinstance(model_pool, dict):
        model_pool = {}

    model_ids = list(sorted(model_pool.keys()))

    chairman_pool = repaired_memory.get("chairman_pool")
    if not isinstance(chairman_pool, dict):
        chairman_pool = {}

    chairman_ids = list(sorted(chairman_pool.keys()))

    chairman_active = repaired_memory.get("chairman_active")
    chairman_active = chairman_active.strip() if (isinstance(chairman_active, str) and chairman_active.strip() in chairman_ids) else None
    if chairman_active is None:
        if chairman_ids:
            chairman_active = chairman_ids[0]
        else:
            if model_ids:
                chairman_active = model_ids[0]

    chairman_specs = chairman_pool.get(chairman_active)
    if not isinstance(chairman_specs, dict):
        chairman_specs = {}

    chairman_role = "chairman"
    chairman_id = chairman_active
    
    chairman_provider = chairman_specs.get("provider")
    chairman_provider = chairman_provider.strip() if isinstance(chairman_provider, str) else ""

    chairman_provider_model = chairman_specs.get("provider_model")
    chairman_provider_model = chairman_provider_model.strip() if isinstance(chairman_provider_model, str) else ""

    chairman_params = chairman_specs.get("params")
    if not isinstance(chairman_params, dict):
        chairman_params = {}
    chairman_params_dictionary = {}

    temperature = chairman_params.get("temperature")
    if not isinstance(temperature, (int, float)) or not(0.0 <= float(temperature) <= 3.0):
        temperature = 0.0
    temperature = float(temperature)
    chairman_params_dictionary["temperature"] = temperature
    chairman_params = chairman_params_dictionary

    chairman_cost_tier = chairman_specs.get("cost_tier")
    chairman_cost_tier = chairman_cost_tier.strip() if isinstance(chairman_cost_tier, str) else ""

    directory_structure = repaired_memory.get("directory_structure")
    if not isinstance(directory_structure, dict):
        directory_structure = {}

    final_model = repaired_memory.get("final_model")
    final_model = final_model.strip() if isinstance(final_model, str) else ""
    if not final_model:
        if model_ids:
            final_model = model_ids[0]

    timeout_defaults = repaired_memory.get("timeout_defaults")
    if not isinstance(timeout_defaults, dict):
        timeout_defaults = {}

    chairman_timeout_s = timeout_defaults.get("chairman_timeout_s")
    if not isinstance(chairman_timeout_s, (int, float)) or not (300 <= int(chairman_timeout_s) <= 360):
        chairman_timeout_s = 360
    chairman_timeout_s = int(chairman_timeout_s)

    code_directory = directory_structure.get(final_model)
    if not isinstance(code_directory, dict):
        code_directory = {}

    file_paths = extract_file_paths(code_directory)
    for file in file_paths:
        path = Path(file).resolve()
        if path.exists() and path.is_file():
            content_dictionary = {
                "path": str(path),
                "content": path.read_text(encoding="utf-8")
            }
            code_review.append(content_dictionary)

    code_review_dictionary = {"current_code": code_review}
    
    task_json = json.dumps(task, sort_keys=True, separators=(",", ":"))
    current_code_json = json.dumps(code_review_dictionary, sort_keys=True, separators=(",", ":"))

    system_text = f"{rules}\n\n{chairman_prompt}".strip()
    user_text = (
        f"TASK_JSON:\n{task_json}\n\n"
        f"CURRENT_CODE_JSON:\n{current_code_json}\n"
    )

    invoke_payload = {
        "call_id": f"{chairman_role}_{chairman_id}",
        "agent_id": chairman_role,
        "model_id": chairman_id,
        "provider": chairman_provider,
        "provider_model": chairman_provider_model,
        "system_text": system_text,
        "user_text": user_text,
        "params": chairman_params,
        "timeout_s": chairman_timeout_s,
        "metadata": {
            "run_id": run_id,
            "cost_tier": chairman_cost_tier,
            "phase": phase
        }
    }

    chairman_results = run_provider(invoke_payload)
    chairman_output = chairman_results.get("output")
    loaded_chairman_output = load_output(chairman_output)
    next_priorities = []
    if loaded_chairman_output is not None:
        next_priorities = parse_priorities(loaded_chairman_output)

    chairman_summary_store = repaired_memory.get("chairman_summary_store")
    if not isinstance(chairman_summary_store, dict):
        chairman_summary_store = {}

    iterate = chairman_summary_store.get("iterate")
    if not isinstance(iterate, dict):
        iterate = {}

    current_next_priorities = iterate.get("next_priorities")
    if not isinstance(current_next_priorities, list):
        current_next_priorities = []
    current_next_priorities = [string for string in current_next_priorities if isinstance(string, str)]
    for priority in current_next_priorities:
        if priority not in next_priorities:
            next_priorities.append(priority)

    iterate["next_priorities"] = next_priorities
    chairman_summary_store["iterate"] = iterate
    repaired_memory["chairman_summary_store"] = chairman_summary_store

    return repaired_memory

def write_memory(state: Dict[str, Any]) -> Dict[str, Any]:

    print("------------------------------------------------------------------------")
    print("-------------------------Writing-Memory---------------------------------")
    print("------------------------------------------------------------------------")

    prompts = state.get("prompts")
    if not isinstance(prompts, dict):
        prompts = {}

    root = state.get("root")
    root = root.strip() if isinstance(root, str) else ""
    root = Path(root).resolve() if root else Path(os.getcwd()).resolve()

    task = state.get("task")
    if not isinstance(task, dict):
        task = {}

    task_directory = root / "task"
    task_directory.mkdir(parents=True, exist_ok=True)

    task_path = task_directory / "task.json"
    prev_task_path = root / "task" / "previous_task.json"

    if task_path.exists():
        task_path.replace(prev_task_path)

    try: 
        with task_path.open("w", encoding="utf-8") as fh:
            json.dump(task, fh, sort_keys=True, separators=(",", ":"), indent=2)
    except Exception as e:
        print("Updating task.json error: ", e)

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

    memory = state.get("memory")
    if not isinstance(memory, dict):
        memory = {}

    run_id = memory.get("current_run_id")
    memory["current_run_id"] = next_run_id(run_id)
    
    run_id = run_id.strip() if isinstance(run_id, str) else "run_000000"
    memory["last_run_id"] = run_id

    exploration = memory.get("exploration")
    if not isinstance(exploration, dict):
        exploration = {}
    exploration_dictionary = {}

    warmup_runs = exploration.get("warmup_runs")
    if not isinstance(warmup_runs, (int, float)) or not(0 <= int(warmup_runs) <= 5):
        warmup_runs = 3
    warmup_runs = int(warmup_runs)
    exploration_dictionary["warmup_runs"] = warmup_runs

    runs_completed = exploration.get("runs_completed")
    if not isinstance(runs_completed, (int, float)):
        runs_completed = 0
    runs_completed = int(runs_completed) + 1
    exploration_dictionary["runs_completed"] = runs_completed
    memory["exploration"] = exploration_dictionary

    overview_requried = True if (runs_completed % 3 == 0 and runs_completed >=3) else False

    if runs_completed == warmup_runs:
        role_model_stats = memory.get("role_model_stats")
        if not isinstance(role_model_stats, dict):
            role_model_stats = {}
        
        architect_stats = role_model_stats.get("architect")
        if not isinstance(architect_stats, dict):
            architect_stats = {}

        best_model = ""
        best_ucb = float("-inf")
        model_ids = list(sorted(architect_stats.keys()))
        for model_id in model_ids:
            model_stats = architect_stats.get(model_id)
            if not isinstance(model_stats, dict):
                model_stats = {}
            ucb = model_stats.get("ucb")
            if not isinstance(ucb, (int, float)):
                ucb = 0.0
            ucb = float(ucb)
            if ucb > best_ucb:
                best_ucb = ucb
                best_model = model_id

        if best_model:
            memory["final_model"] = best_model

    repaired_memory = repair_memory(memory, first_run, root)
    if overview_requried:
        repaired_memory = chairman_overview(repaired_memory, prompts, task)

    memory_dir = root / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    memory_json_path = memory_dir / "memory.json"
    prev_memory_path = root / "memory" / "previous_memory.json"

    if memory_json_path.exists():
        memory_json_path.replace(prev_memory_path)

    try: 
        with memory_json_path.open("w", encoding="utf-8") as fh:
            json.dump(repaired_memory, fh, sort_keys=True, separators=(",", ":"), indent=2)
    except Exception as e:
        print("Updating state.json error: ", e)

    return {"memory": repaired_memory}

def update_files(state: Dict[str, Any]) -> Dict[str, Any]:

    task = state.get("task")
    if not isinstance(task, dict):
        task = {}

    phase = task.get("phase")
    phase = phase.strip().lower() if (isinstance(phase, str) and phase.strip().lower() in PHASES) else "bootstrap"

    memory = state.get("memory")
    if not isinstance(memory, dict):
        memory = {}

    final_model = memory.get("final_model")
    final_model = final_model.strip() if isinstance(final_model, str) else ""

    directory_structure = memory.get("directory_structure")
    if not isinstance(directory_structure, dict):
        directory_structure = {}

    chairman_edits = memory.get("chairman_edits")
    if not isinstance(chairman_edits, dict):
        chairman_edits = {}

    if phase == "bootstrap":
        model_pool = memory.get("model_pool")
        if not isinstance(model_pool, dict):
            model_pool = {}

        model_ids = list(sorted(model_pool.keys()))

        bootstrap_edits = chairman_edits.get(phase)
        if not isinstance(bootstrap_edits, dict):
            bootstrap_edits = {}

        for model_id in model_ids:
            code_directory = directory_structure.get(model_id)
            if not isinstance(code_directory, dict):
                code_directory = {}

            base_path = code_directory.get("path")
            if isinstance(base_path, str) and base_path.strip():
                base_path = Path(base_path.strip()).resolve()
            else:
                base_path = Path(os.getcwd()).resolve() / "code" / str(model_id)
                base_path.mkdir(parents=True, exist_ok=True)

            model_edits = bootstrap_edits.get(model_id)
            if not isinstance(model_edits, dict):
                model_edits = {}
            
            edits = model_edits.get("approved_edits")
            if not isinstance(edits, list):
                edits = []           
            for edit in edits:
                if isinstance(edit, dict):
                    path = edit.get("path")
                    path = path.strip() if isinstance(path, str) else ""
                    if not path:
                        continue
                    path = Path(path).resolve()
                    if not is_within_base(path, base_path):
                        continue
        
                    content = edit.get("content")
                    content = content.strip() if isinstance(content, str) else ""
                    if not content:
                        continue

                    try: 
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text(content, encoding="utf-8")
                    except Exception as e:
                        print(f"Updating {str(path)} error: ", e)

    elif phase == "iterate":
        if not final_model:
            return {}

        code_directory = directory_structure.get(final_model)
        if not isinstance(code_directory, dict):
            code_directory = {}

        base_path = code_directory.get("path")
        if isinstance(base_path, str) and base_path.strip():
            base_path = Path(base_path.strip()).resolve()
        else:
            base_path = Path(os.getcwd()).resolve() / "code" / str(final_model)
            base_path.mkdir(parents=True, exist_ok=True)

        iterate_edits = chairman_edits.get(phase)
        if not isinstance(iterate_edits, dict):
            iterate_edits = {}

        edits = iterate_edits.get("approved_edits")
        if not isinstance(edits, list):
            edits = []
        for edit in edits:
            if isinstance(edit, dict):
                path = edit.get("path")
                path = path.strip() if isinstance(path, str) else ""
                if not path:
                    continue
                path = Path(path).resolve()
                if not is_within_base(path, base_path):
                    continue

                content = edit.get("content")
                content = content.strip() if isinstance(content, str) else ""
                if not content:
                    continue

                try: 
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, encoding="utf-8")
                except Exception as e:
                    print(f"Updating {str(path)} error: ", e)

    return {}

def unparse(node: ast.AST) -> str:
    
    try:
        return ast.unparse(node) 
    except Exception:
        return ast.dump(node, include_attributes=False)


def is_constant_name(name: str) -> bool:
    
    if not name:
        return False

    constant_name = name.lstrip("_")
    if not constant_name:
        return False

    return all(char.isupper() or char.isdigit() or char == "_" for char in constant_name) and any(char.isalpha() for char in constant_name)

def dedupe_str(values: List[str]) -> List[str]:
    
    seen = set()
    output = []
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    
    return output

def dedupe_constants(constants: List[Dict[str, str]]) -> List[Dict[str, str]]:
    
    seen = set()
    output = []
    for constant in constants:
        name = constant.get("name")
        name = name.strip() if isinstance(name, str) else ""
        if not name:
            continue
        value = constant.get("value")
        value = value if isinstance(value, str) else ""
        if not value:
            continue
        dedupe_value = (name, value)
        constant_dictionary = {"name": name, "value": value}
        if dedupe_value not in seen:
            seen.add(dedupe_value)
            output.append(constant_dictionary)
    
    return output

def extract_functions_imports_constants(content: str) -> Tuple[List[str], List[str], List[Dict[str, str]]]:

    if not isinstance(content, str):
        return [], [], []

    try:
        tree = ast.parse(content)
    except Exception:
        return [], [], []

    functions: List[str] = []
    imports: List[str] = []
    constants: List[Dict[str, str]] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if isinstance(node.name, str) and node.name.strip():
                functions.append(node.name.strip())

        elif isinstance(node, ast.Import):
            parts = []
            for alias in node.names:
                if not isinstance(alias, ast.alias):
                    continue
                name = alias.name.strip() if isinstance(alias.name, str) else ""
                if not name:
                    continue
                if alias.asname:
                    asname = alias.asname.strip() if isinstance(alias.asname, str) else ""
                    if not asname:
                        continue
                    parts.append(f"{name} as {asname}")
                else:
                    parts.append(name)
            if parts:
                imports.append("import " + ", ".join(parts))

        elif isinstance(node, ast.ImportFrom):
            module = node.module.strip() if isinstance(node.module, str) else ""
            level = int(node.level or 0)
            prefix = "." * level
            from_module = prefix + module if module else prefix or ""
            if not from_module:
                continue
            parts = []
            for alias in node.names:
                if not isinstance(alias, ast.alias):
                    continue
                name = alias.name.strip() if isinstance(alias.name, str) else ""
                if not name:
                    continue
                if alias.asname:
                    asname = alias.asname.strip() if isinstance(alias.asname, str) else ""
                    if asname:
                        parts.append(f"{name} as {asname}")
                    else:
                        parts.append(name)
                else:
                    parts.append(name)
            if from_module and parts:
                imports.append(f"from {from_module} import " + ", ".join(parts))

        elif isinstance(node, ast.Assign):
            value_str = unparse(node.value)
            value_str = value_str.strip() if isinstance(value_str, str) else ""
            if not value_str:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id.strip() if isinstance(target.id, str) else ""
                    if not name:
                        continue
                    if is_constant_name(name):
                        constants.append({"name": name, "value": value_str})

        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                name = node.target.id.strip() if isinstance(node.target.id, str) else ""
                if not name:
                    continue
                if is_constant_name(name):
                    value_str = unparse(node.value) if node.value is not None else ""
                    value_str = value_str.strip() if isinstance(value_str, str) else ""
                    if not value_str:
                        continue
                    constants.append({"name": name, "value": value_str})

    return dedupe_str(functions), dedupe_str(imports), dedupe_constants(constants)

def normalize_code_directory(code_directory: Dict[str, Any], base_path: Path) -> Dict[str, Any]:
    
    if not isinstance(code_directory, dict):
        code_directory = {}

    path = code_directory.get("path")
    if not isinstance(path, str) or not path.strip():
        code_directory["path"] = str(base_path)

    if not isinstance(code_directory.get("dirs"), dict):
        code_directory["dirs"] = {}

    if not isinstance(code_directory.get("files"), list):
        code_directory["files"] = []

    return code_directory

def safe_relpath(file_path: Path, base_dir: Path) -> str | None:
    
    try:
        path = os.path.abspath(str(Path(file_path).resolve()))
        directory = os.path.abspath(str(Path(base_dir).resolve()))

        if os.name == "nt":
            path_ = os.path.normcase(path)
            directory_ = os.path.normcase(directory)
        else:
            path_ = path
            directory_ = directory

        if os.path.commonpath([path_, directory_]) != directory_:
            return None

        return os.path.relpath(path, directory)
    except Exception:
        return None

def update_code_directory(path: Path, base_path: Path, code_directory: Dict[str, Any], content: str) -> Dict[str, Any]:

    if path.exists() and path.is_file():
        relative_path = safe_relpath(path, base_path)
        if not relative_path:
            return code_directory
        relative_path = Path(relative_path)
        parts = relative_path.parts
        module = parts[-1]
        dirs = list(parts[:-1])

        if len(dirs) >= 1:
            running_path = base_path
            running_code_dirs = code_directory.get("dirs")
            if not isinstance(running_code_dirs, dict):
                running_code_dirs = {}
                code_directory["dirs"] = running_code_dirs
            for idx, dir_ in enumerate(dirs):
                if dir_ not in running_code_dirs:
                    running_path = running_path / dir_
                    running_code_dirs[dir_] = {"path": "", "dirs": {}, "files": []}
                    running_code_dirs[dir_]["path"] = str(running_path)
                    if idx == len(dirs) - 1:
                        running_code_dirs = running_code_dirs[dir_]
                    else: 
                        running_code_dirs = running_code_dirs[dir_]["dirs"]
                else:
                    running_path = running_path / dir_
                    current_path = running_code_dirs[dir_].get("path")
                    current_path = current_path.strip() if isinstance(current_path, str) else ""
                    if current_path != str(running_path):
                        running_code_dirs[dir_]["path"] = str(running_path)
                    current_dir = running_code_dirs[dir_].get("dirs")
                    if not isinstance(current_dir, dict):
                        current_dir = {}
                    running_code_dirs[dir_]["dirs"] = current_dir
                    if idx == len(dirs) - 1:
                        running_code_dirs = running_code_dirs[dir_]
                    else: 
                        running_code_dirs = running_code_dirs[dir_]["dirs"]
            current_files = running_code_dirs.get("files")
            if not isinstance(current_files, list):
                current_files = []
                running_code_dirs["files"] = current_files
            module_list = [file.get("module").strip() for file in current_files if isinstance(file, dict) and isinstance(file.get("module"), str)]
            running_path = running_path / module
            if module not in module_list:
                current_files.append({"path": "", "module": "", "functions": [], "imports": [], "constants": []})
                current_files[-1]["path"] = str(running_path)
                current_files[-1]["module"] = module
                functions, imports, constants = extract_functions_imports_constants(content)
                current_files[-1]["functions"] = functions
                current_files[-1]["imports"] = imports
                current_files[-1]["constants"] = constants
            else:
                for idx, file in enumerate(current_files):
                    if not isinstance(file, dict):
                        continue
                    file_module = file.get("module").strip() if isinstance(file.get("module"), str) else ""
                    if not file_module:
                        continue
                    if module == file_module:
                        current_files[idx]["path"] = str(running_path)
                        current_files[idx]["module"] = module
                        functions, imports, constants = extract_functions_imports_constants(content)
                        current_files[idx]["functions"] = functions
                        current_files[idx]["imports"] = imports
                        current_files[idx]["constants"] = constants
        else:
            module_path = base_path / module
            functions, imports, constants = extract_functions_imports_constants(content)
            files = code_directory.get("files")
            if not isinstance(files, list):
                files = []
                code_directory["files"] = files
            current_files = [file.get("module").strip() for file in files if isinstance(file, dict) and isinstance(file.get("module"), str)]
            if module not in current_files:
                code_directory["files"].append({"path": "", "module": "", "functions": [], "imports": [], "constants": []})
                code_directory["files"][-1]["path"] = str(module_path)
                code_directory["files"][-1]["module"] = str(module)
                code_directory["files"][-1]["functions"] = functions
                code_directory["files"][-1]["imports"] = imports
                code_directory["files"][-1]["constants"] = constants
            else:
                for idx, file in enumerate(files):
                    if not isinstance(file, dict):
                        continue
                    file_module = file.get("module").strip() if isinstance(file.get("module"), str) else ""
                    if not file_module:
                        continue
                    if module == file_module:
                        code_directory["files"][idx]["path"] = str(module_path)
                        code_directory["files"][idx]["module"] = str(module)
                        code_directory["files"][idx]["functions"] = functions
                        code_directory["files"][idx]["imports"] = imports
                        code_directory["files"][idx]["constants"] = constants

    return code_directory

def update_directory_structure(state: Dict[str, Any]) -> Dict[str, Any]:

    root = state.get("root")
    root = root.strip() if isinstance(root, str) else ""
    if not root:
        root = Path(os.getcwd()).resolve()
    else:
        root = Path(root).resolve()

    task = state.get("task")
    if not isinstance(task, dict):
        task = {}

    phase = task.get("phase")
    phase = phase.strip().lower() if (isinstance(phase, str) and phase.strip().lower() in PHASES) else "bootstrap"

    memory = state.get("memory")
    if not isinstance(memory, dict):
        memory = {}

    directory_structure = memory.get("directory_structure")
    if not isinstance(directory_structure, dict):
        directory_structure = {}

    base_path = directory_structure.get("base_path")
    base_path = Path(base_path.strip()).resolve() if isinstance(base_path, str) else None
    if base_path is None:
        base_path = root / "code"
    base_path.mkdir(parents=True, exist_ok=True)
    directory_structure["base_path"] = str(base_path)

    chairman_edits = memory.get("chairman_edits")
    if not isinstance(chairman_edits, dict):
        chairman_edits = {}

    model_pool = memory.get("model_pool")
    if not isinstance(model_pool, dict):
        model_pool = {}

    model_ids = list(sorted(model_pool.keys()))

    final_model = memory.get("final_model")
    final_model = final_model.strip() if isinstance(final_model, str) else ""
    if not final_model:
        if model_ids:
            final_model = model_ids[0]

    if phase == "bootstrap":
        bootstrap_edits = chairman_edits.get(phase)
        if not isinstance(bootstrap_edits, dict):
            bootstrap_edits = {}

        for model_id in model_ids:
            code_directory = directory_structure.get(model_id)
            if not isinstance(code_directory, dict):
                code_directory = {}

            base_path = code_directory.get("path")
            if isinstance(base_path, str) and base_path.strip():
                base_path = Path(base_path.strip()).resolve()
            else:
                base_path = Path(os.getcwd()).resolve() / "code" / str(model_id)
                base_path.mkdir(parents=True, exist_ok=True)    

            code_directory = normalize_code_directory(code_directory, base_path)

            model_edits = bootstrap_edits.get(model_id)
            if not isinstance(model_edits, dict):
                model_edits = {}

            edits = model_edits.get("approved_edits")
            if not isinstance(edits, list):
                edits = []           
            for edit in edits:
                if isinstance(edit, dict):
                    path = edit.get("path")
                    path = path.strip() if isinstance(path, str) else ""
                    if not path:
                        continue
                    path = Path(path).resolve()
                    if not is_within_base(path, base_path):
                        continue
                    content = edit.get("content")
                    content = content.strip() if isinstance(content, str) else ""
                    if not content:
                        continue
                    code_directory = update_code_directory(path, base_path, code_directory, content)
            directory_structure.setdefault(model_id, {})
            directory_structure[model_id] = normalize_code_directory(code_directory, base_path)

    elif phase == "iterate":
        code_directory = directory_structure.get(final_model)
        if not isinstance(code_directory, dict):
            code_directory = {}

        base_path = code_directory.get("path")
        if isinstance(base_path, str) and base_path.strip():
            base_path = Path(base_path.strip()).resolve()
        else:
            base_path = Path(os.getcwd()).resolve() / "code" / str(final_model)
            base_path.mkdir(parents=True, exist_ok=True)  

        code_directory = normalize_code_directory(code_directory, base_path)

        model_edits = chairman_edits.get(phase)
        if not isinstance(model_edits, dict):
            model_edits = {}     

        edits = model_edits.get("approved_edits")
        if not isinstance(edits, list):
            edits = []           
        for edit in edits:
            if isinstance(edit, dict):
                path = edit.get("path")
                path = path.strip() if isinstance(path, str) else ""
                if not path:
                    continue
                path = Path(path).resolve()
                if not is_within_base(path, base_path):
                    continue
                content = edit.get("content")
                content = content.strip() if isinstance(content, str) else ""
                if not content:
                    continue
                code_directory = update_code_directory(path, base_path, code_directory, content)
        directory_structure.setdefault(final_model, {})
        directory_structure[final_model] = normalize_code_directory(code_directory, base_path)
    
    memory["directory_structure"] = directory_structure
              
    return {"memory": memory}