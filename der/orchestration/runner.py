import json
import time
import os
from copy import deepcopy
from pathlib import Path
from typing import Dict, Any, List, Tuple
from utils.utils import is_within_base, load_output
from .provider import invoke_gemini, invoke_anthropic, invoke_openai

ROLES = ["architect", "implementer"]
ROLE_ORDER = {"architect": 0, "implementer": 1}
PHASES = {"bootstrap", "iterate"}

def validate_call_id_contract(agent_calls: List[Dict[str, Any]]) -> bool:
    
    validated = True
    for call in agent_calls:
        role = str(call.get("agent_id",""))
        model_id  = str(call.get("model_id",""))
        call_id  = str(call.get("call_id",""))
        expected = f"{role}_{model_id}"
        if call_id != expected:
            validated = False
    
    return validated

def build_role_model_to_call_id(agent_calls: List[Dict[str, Any]]) -> Dict[Tuple[str, str], str]:
    
    call_ids: Dict[Tuple[str, str], str] = {}
    for call in agent_calls:
        role = str(call.get("agent_id",""))
        model_id  = str(call.get("model_id",""))
        call_id  = str(call.get("call_id",""))
        if role and model_id and call_id:
            call_ids[(role, model_id)] = call_id
    
    return call_ids

def run_provider(invoke_payload: Dict[str, Any]) -> Dict[str, Any]:

    start = time.time()
    agent_results: Dict[str, Any] = {}

    error = None
    invoke_payload = deepcopy(invoke_payload)
    provider = invoke_payload.get("provider", None)
    if not isinstance(provider, str):
        provider = None

    if provider is None:
        output, tokens, error = "", {}, "invalid provider"

    else:
        try:

            if provider== "gemini":
                output, tokens = invoke_gemini(invoke_payload)
                              
            elif provider == "anthropic":
                output, tokens = invoke_anthropic(invoke_payload)

            elif provider == "openai":
                output, tokens = invoke_openai(invoke_payload)
                
            else:
                output, tokens, error = "", {}, "unknown provider"

            if isinstance(tokens, dict) and "error" in tokens:
                error = tokens["error"]

        except Exception as e:

            output, tokens, error = "", {}, f"{type(e).__name__}: {e}"

    latency_ms = int((time.time() - start) * 1000)
    agent_results["agent_id"] = invoke_payload.get("agent_id", "")
    agent_results["model_id"] = invoke_payload.get("model_id", "")
    agent_results["output"] = output
    agent_results["tokens"] = tokens
    agent_results["cost"] = None
    agent_results["latency_ms"] = latency_ms
    agent_results["error"] = error

    return agent_results

def parse_implementer_output(model_output: Dict[str, Any]) -> Dict[str, Any]:

    implementer_schema_object: Dict[str, Any] = {}
    
    if model_output is None or not isinstance(model_output, dict):
        implementer_schema_object = {"modules_added_and_updated": []}
        return implementer_schema_object

    else:
        modules_added_and_updated = model_output.get("modules_added_and_updated")
        if isinstance(modules_added_and_updated, list):
            modules_list = []
            module_keys = ["proposal_ids", "path", "content", "included_functions", "included_imports", "included_constants"]
            for module in modules_added_and_updated:
                if isinstance(module, dict):
                    module_dictionary = {}
                    for key, value in module.items():
                        current_key = key.strip().lower() if isinstance(key, str) else ""
                        if current_key in module_keys:
                            if current_key == "proposal_ids":
                                if isinstance(value, list):
                                    value = [string for string in value if isinstance(string, str)]
                                else:
                                    value = []
                                module_dictionary[current_key] = value
                            elif current_key == "path":
                                if isinstance(value, str):
                                    value = value.strip()
                                    if value:
                                        module_dictionary[current_key] = value
                                    else:
                                        continue
                                else:
                                    continue 
                            elif current_key == "content":
                                if isinstance(value, str):
                                    value = value.strip()
                                    if value:
                                        module_dictionary[current_key] = value
                                    else:
                                        continue
                                else:
                                    continue
                            elif current_key == "included_functions":
                                if isinstance(value, list):
                                    value = [string for string in value if isinstance(string, str)]
                                else:
                                    value = []
                                module_dictionary[current_key] = value
                            elif current_key == "included_imports":
                                if isinstance(value, list):
                                    value = [string for string in value if isinstance(string, str)]
                                else:
                                    value = []
                                module_dictionary[current_key] = value   
                            elif current_key == "included_constants":
                                included_constants_list = []
                                if isinstance(value, list):
                                    for constant in value:
                                        if isinstance(constant, dict):
                                            constant_dictionary = {}
                                            constant_name = constant.get("name")
                                            constant_name = constant_name.strip() if isinstance(constant_name, str) else None
                                            if constant_name is None:
                                                continue
                                            constant_dictionary["name"] = constant_name
                                            constant_value = constant.get("value")
                                            constant_dictionary["value"] = constant_value
                                            included_constants_list.append(constant_dictionary)
                                    module_dictionary[current_key] = included_constants_list
                                else:
                                    module_dictionary[current_key] = []
                    modules_list.append(module_dictionary)
            implementer_schema_object["modules_added_and_updated"] = modules_list
        else:
            implementer_schema_object["modules_added_and_updated"] = []

    return implementer_schema_object

def parse_architect_output(model_output: Dict[str, Any]) -> Dict[str, Any]:

    architect_schema_object: Dict[str, Any] = {}

    if model_output is None or not isinstance(model_output, dict):
        architect_schema_object = {"design_moves": []}
        return architect_schema_object

    else:
        design_moves = model_output.get("design_moves")
        if isinstance(design_moves, list):
            design_moves_list = []
            design_move_keys = ["proposal_id", "path", "function", "goal", "constraints"]
            for move in design_moves:
                if isinstance(move, dict):
                    dictionary = {}
                    for key, value in move.items():
                        current_key = key.strip().lower() if isinstance(key, str) else ""
                        if current_key in design_move_keys:
                            if current_key == "proposal_id":
                                if isinstance(value, str) and value.strip():
                                    dictionary[current_key] = value.strip()
                                else:
                                    continue
                            elif current_key == "path":
                                if isinstance(value, str) and value.strip():
                                    dictionary[current_key] = value.strip()
                                else:
                                    continue
                            elif current_key == "function":
                                if isinstance(value, str) and value.strip():
                                    dictionary[current_key] = value.strip()
                                else:
                                    continue
                            elif current_key == "goal":
                                if isinstance(value, str):
                                    dictionary[current_key] = value.strip()
                                else:
                                    dictionary[current_key] = ""
                            elif current_key == "constraints":
                                if isinstance(value, list):
                                    value = [string for string in value if isinstance(string, str)]
                                    dictionary[current_key] = value
                                else:
                                    dictionary[current_key] = []
                    design_moves_list.append(dictionary)
            architect_schema_object["design_moves"] = design_moves_list
        else:
            architect_schema_object["design_moves"] = []

        return architect_schema_object

def upload_relevant_code(architect_output: Dict[str, Any], model_directory: Path) -> Dict[str, Any]:

    if not isinstance(architect_output, dict):
        return {}

    code_directory: Dict[str, Any] = {}

    design_moves = architect_output.get("design_moves")
    if not isinstance(design_moves, list):
        return {}

    new_modules: List[Dict[str, Any]] = []
    new_modules_uploaded_paths: List[Path] = []

    module_patches: List[Dict[str, Any]] = []
    module_patches_uploaded_paths: List[Path] = []

    for move in design_moves:
        if isinstance(move, dict):
            new_files = False
            content = None
            proposal_id = move.get("proposal_id")
            proposal_id = proposal_id.strip() if isinstance(proposal_id, str) else ""
            path = move.get("path")
            path = path.strip() if isinstance(path, str) else ""
            if not path or not is_within_base(Path(path).resolve(), model_directory):
                print("not path", not path)
                print("not is_within_base()", not is_within_base(Path(path).resolve(), model_directory))
                continue
            else:
                path = Path(path).resolve()
                if not path.exists() or not path.is_file():
                    new_files = True
            function = move.get("function")
            function = function.strip() if isinstance(function, str) else ""
            if not function:
                print("not function", not function)
                continue
            goal = move.get("goal")
            goal = goal.strip() if isinstance(goal, str) else ""
            constraints = move.get("constraints")
            if not isinstance(constraints, list):
                constraints = []
            constraints = [string for string in constraints if isinstance(string, str)]
            edits_dictionary = {
                "proposal_id": proposal_id,
                "function": function,
                "goal": goal,
                "constraints": constraints,
            }
            if not new_files:
                if path in module_patches_uploaded_paths:
                    for patch in module_patches:
                        if isinstance(patch, dict):
                            module_path = Path(patch.get("module_path")).resolve()
                            if module_path == path:
                                if "edits" in patch:
                                    patch["edits"].append(edits_dictionary)
                else:
                    content = path.read_text(encoding="utf-8")
                    module_patch = {
                        "module_path": str(path),
                        "edits": [edits_dictionary],
                        "module_content": content
                    }
                    module_patches.append(module_patch)
                    module_patches_uploaded_paths.append(path)
            else:
                if path in new_modules_uploaded_paths:
                    for patch in new_modules:
                        if isinstance(patch, dict):
                            module_path = Path(patch.get("module_path")).resolve()
                            if module_path == path:
                                if "edits" in patch:
                                    patch["edits"].append(edits_dictionary)
                else:
                    module_patch = {
                        "module_path": str(path),
                        "edits": [edits_dictionary]
                    }                    
                    new_modules.append(module_patch)
                    new_modules_uploaded_paths.append(path)
    
    code_directory["new_modules"] = new_modules
    code_directory["module_patches"] = module_patches

    return code_directory

def run_agents(state: Dict[str, Any]) -> Dict[str, Any]:

    print("------------------------------------------------------------------------")
    print("-------------------------Calling-Agents---------------------------------")
    print("------------------------------------------------------------------------")

    agent_results: Dict[str, Any] = {}

    agent_calls = state.get("agent_calls")
    if not isinstance(agent_calls, list):
        agent_calls = []

    role_assignments = state.get("role_assignments")
    if not isinstance(role_assignments, dict):
        role_assignments = {}

    run_id = state.get("run_id")
    run_id = run_id.strip() if isinstance(run_id, str) else "run_000001"

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

    final_model = memory.get("final_model")
    final_model = final_model.strip() if isinstance(final_model, str) else "M1"

    model_pool = memory.get("model_pool")
    if not isinstance(model_pool, dict):
        model_pool = {}

    timeout_defaults = memory.get("timeout_defaults")
    if not isinstance(timeout_defaults, dict):
        timeout_defaults = {}

    run_agents_timeout_s = timeout_defaults.get("run_agents_timeout_s")
    if not isinstance(run_agents_timeout_s, (int, float)) or not(300 <= int(run_agents_timeout_s) <= 360):
        run_agents_timeout_s = 300
    run_agents_timeout_s = int(run_agents_timeout_s)

    exploration = memory.get("exploration")
    if not isinstance(exploration, dict):
        exploration = {}

    runs_completed = exploration.get("runs_completed")
    if not isinstance(runs_completed, (int, float)):
        runs_completed = 0
    runs_completed = int(runs_completed)

    contract_validated = validate_call_id_contract(agent_calls)
    role_model_to_call_id = None

    if not contract_validated:
        role_model_to_call_id = build_role_model_to_call_id(agent_calls)

    agent_calls.sort(key=lambda idx: (ROLE_ORDER.get(idx.get("agent_id",""), float("inf")), str(idx.get("model_id","")), str(idx.get("call_id",""))))

    for call in agent_calls:
        
        call_id = call.get("call_id").strip()
        role = call.get("agent_id").strip()
        model_id = call.get("model_id").strip()
        task = call.get("task")
        rules = call.get("rules").strip()
        role_prompt = call.get("role_prompt").strip()
        agent_weight = call.get("agent_weight")
        chairman_summary = call.get("chairman_summary")
        
        specs = model_pool.get(model_id)
        if not isinstance(specs, dict):
            specs = {}
        
        provider = specs.get("provider")

        if phase == "bootstrap":
            model_directory = base_path / model_id
            model_directory.mkdir(parents=True, exist_ok=True)
            
            code_model_directory = directory_structure.get(model_id)
            if not isinstance(code_model_directory, dict):
                code_model_directory = {}
            
        elif phase == "iterate":
            model_directory = base_path / final_model
            model_directory.mkdir(parents=True, exist_ok=True)
            
            code_model_directory = directory_structure.get(final_model)
            if not isinstance(code_model_directory, dict):
                code_model_directory = {}

        task_json = json.dumps(task, sort_keys=True, separators=(",", ":"))
        directory_structure_json = json.dumps(code_model_directory, sort_keys=True, separators=(",", ":"))
        chairman_summary_json = json.dumps(chairman_summary, sort_keys=True, separators=(",", ":"))

        system_text = f"{rules}\n\n{role_prompt}".strip()
        user_text = (
            f"TASK_JSON:\n{task_json}\n\n"
            f"DIRECTORY_STRUCTURE_JSON:\n{directory_structure_json}\n"
        )

        if role == "architect":
            user_text += f"\nCHAIRMAN_SUMMARY_JSON:\n{chairman_summary_json}\n"
        elif role == "implementer":
            if phase == "iterate":
                architect_model = role_assignments.get("architect")
                architect_model = architect_model.strip() if isinstance(architect_model, str) else ""
            else:
                architect_model = model_id 
            architect_layer_id = f"architect_{architect_model}" if contract_validated else role_model_to_call_id.get(("architect", architect_model), None)
            if architect_layer_id is not None:
                architect_provider_output = agent_results.get(architect_layer_id)
                if not isinstance(architect_provider_output, dict):
                    architect_provider_output = {}
                architect_output = architect_provider_output.get("output")
                if not isinstance(architect_output, dict):
                    architect_output = {}
                current_code = upload_relevant_code(architect_output, model_directory)
                if not isinstance(current_code, dict):
                    current_code = {}
                current_code_json = json.dumps(current_code, sort_keys=True, separators=(",", ":"))
                user_text += f"EXISTING_MODULE_CODE:\n{current_code_json}\n"
        
        invoke_payload = {
            "call_id": call.get("call_id"),
            "agent_id": call.get("agent_id"),
            "model_id": model_id,
            "provider": provider,
            "provider_model": specs.get("provider_model", ""),
            "system_text": system_text,
            "user_text": user_text,
            "params": specs.get("params", {}),
            "timeout_s": run_agents_timeout_s,
            "metadata": {
                "run_id": run_id,
                "agent_weight": call.get("agent_weight", 0.5),
                "cost_tier": specs.get("cost_tier", ""),
                "phase": phase,
            },
        }        
        
        provider_output = run_provider(invoke_payload)
        output = provider_output.get("output")
        loaded_output = load_output(output)
        parsed_output = {}
        if loaded_output is not None:
            if role == "architect":
                parsed_output = parse_architect_output(loaded_output)
            elif role == "implementer":
                parsed_output = parse_implementer_output(loaded_output)
        provider_output["output"] = parsed_output
        agent_results[call_id] = provider_output
    
    return {"agent_results": agent_results}