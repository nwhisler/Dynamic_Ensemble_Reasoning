import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Dict, Any, Tuple

PHASES = {"bootstrap", "iterate"}
LANGUAGES = {"python", "c++", "java"}
ROLES = ["architect", "implementer"]
DEFAULT_MODELS = ["M1", "M2"]
COST_TIERS = {"low", "mid", "high"}
PROVIDERS = {"gemini", "openai", "anthropic"}

def calculate_weights(weighted_inputs: Dict[str, Any]) -> Dict[str, Any]:

    weighted_inputs = deepcopy(weighted_inputs) if isinstance(weighted_inputs, dict) else {}

    for role in ROLES:
        role_weight = weighted_inputs.get(role, 0.5)
        if not isinstance(role_weight, (int, float)) or role_weight < 0:
            role_weight = 0.5
        weighted_inputs[role] = float(role_weight)
    weighted_inputs = {role:weighted_inputs[role] for role in ROLES}
    total = sum(weighted_inputs.values())

    if total <= 0.0:
        weighted_inputs = {role:(1/len(ROLES)) for role in ROLES}
    else:
        weighted_inputs = {role:(weighted_inputs[role]/total) for role in ROLES}

    return weighted_inputs

def repair_cell(cell: Any) -> Dict[str, Any]:

    if not isinstance(cell, dict):
        cell = {}
    
    n = cell.get("n")
    if not isinstance(n, (int, float)) or n < 0:
        n = 0
    n = int(n)
    
    mean_reward = cell.get("mean_reward")
    if not isinstance(mean_reward, (int, float)) or not(0.0 <= float(mean_reward) <= 1.0):
        mean_reward = 0.0
    mean_reward = float(mean_reward)
    
    mean_cost = cell.get("mean_cost")
    if not isinstance(mean_cost, (int, float)) or not(0.0 <= float(mean_cost) <= 1.0):
        mean_cost = 0.0
    mean_cost = float(mean_cost)
    
    last_used_run_id = cell.get("last_used_run_id")
    if last_used_run_id is not None and (not isinstance(last_used_run_id, str) or not last_used_run_id.strip()):
        last_used_run_id = None

    ucb = cell.get("ucb")
    if not isinstance(ucb, (int, float)):
        ucb = 0.0
    ucb = float(ucb)
    
    return {"n": n, "mean_reward": mean_reward, "mean_cost": mean_cost, "last_used_run_id": last_used_run_id, "ucb": ucb}

def repair_memory(memory: Dict[str, Any], first_run: bool, root_path: Path) -> Dict[str, Any]:

    if not isinstance(memory, dict):
        memory = {}
    memory_dictionary: Dict[str, Any] = {}

    current_run_id = memory.get("current_run_id")
    current_run_id = current_run_id.strip() if isinstance(current_run_id, str) else "run_000001"
    memory_dictionary["current_run_id"] = current_run_id

    last_run_id = memory.get("last_run_id")
    last_run_id = last_run_id.strip() if isinstance(last_run_id, str) else "run_000000"
    memory_dictionary["last_run_id"] = last_run_id

    weighted_inputs = memory.get("weighted_inputs")
    if not isinstance(weighted_inputs, dict):
        weighted_inputs = {}
    final_weighted_inputs = calculate_weights(weighted_inputs)
    memory_dictionary["weighted_inputs"] = final_weighted_inputs

    model_pool = memory.get("model_pool")
    if not isinstance(model_pool, dict):
        model_pool = {}
    
    model_defaults = {
        "M1": {
            "label": "Gemini 2.5 Pro",
            "cost_tier": "mid",
            "provider": "gemini",
            "provider_model": "gemini-2.5-pro",
            "params": { "temperature": 0.0 }
        },
        "M2": {
            "label": "Claude Sonnet 4.5",
            "cost_tier": "mid",
            "provider": "anthropic",
            "provider_model": "claude-sonnet-4-5-20250929",
            "params": { "temperature": 0.0 }
        }
    }

    for model, model_specs in model_defaults.items():
        if model not in model_pool or not isinstance(model_pool.get(model), dict):
            model_pool[model] = dict(model_specs)
        else:
            model_pool[model].setdefault("label", model_specs["label"])
            cost_tier = model_pool[model].get("cost_tier")
            cost_tier = cost_tier.strip().lower() if isinstance(cost_tier, str) else ""
            if cost_tier not in COST_TIERS:
                model_pool[model]["cost_tier"] = model_specs["cost_tier"]
            
            provider = model_pool[model].get("provider")
            if isinstance(provider, str):
                provider = provider.strip().lower()
            if provider not in PROVIDERS:
                provider = model_specs["provider"]
            model_pool[model]["provider"] = provider

            provider_model = model_pool[model].get("provider_model")
            if not isinstance(provider_model, str) or not provider_model.strip():
                model_pool[model]["provider_model"] = model_specs["provider_model"]
            else:
                model_pool[model]["provider_model"] = provider_model.strip()

            params = model_pool[model].get("params")
            if not isinstance(params, dict):
                params = {}

            temperature = params.get("temperature")
            if not isinstance(temperature, (int, float)) or not(0.0 <= float(temperature) <= 1.0):
                temperature = model_specs["params"]["temperature"]
            params["temperature"] = float(temperature)
            model_pool[model]["params"] = params
    model_pool = {model:{"label":model_pool[model]["label"], 
    "cost_tier":model_pool[model]["cost_tier"],
    "provider":model_pool[model]["provider"],
    "provider_model":model_pool[model]["provider_model"],
    "params":model_pool[model]["params"]} for model in model_defaults.keys()}
    memory_dictionary["model_pool"] = model_pool
    
    model_ids = list(sorted(model_pool.keys()))

    chairman_pool = memory.get("chairman_pool")
    if not isinstance(chairman_pool, dict):
        chairman_pool = {}

    chairman_defaults = {
        "C1": {
        "label": "GPT-4.1 Chairman",
        "provider": "openai",
        "provider_model": "gpt-4.1",
        "params": { "temperature": 0.0 },
        "cost_tier": "mid"
        }
    }

    for chairman, specs in chairman_defaults.items():
        if chairman not in chairman_pool or not isinstance(chairman_pool.get(chairman), dict):
            chairman_pool[chairman] = dict(specs)
        else:
            chairman_pool[chairman].setdefault("label", specs["label"])
            cost_tier = chairman_pool[chairman].get("cost_tier")
            cost_tier = cost_tier.strip().lower() if isinstance(cost_tier, str) else ""
            if cost_tier not in COST_TIERS:
                chairman_pool[chairman]["cost_tier"] = specs["cost_tier"]
            
            provider = chairman_pool[chairman].get("provider")
            if isinstance(provider, str):
                provider = provider.strip().lower()
            if provider not in PROVIDERS:
                provider = specs["provider"]
            chairman_pool[chairman]["provider"] = provider

            provider_model = chairman_pool[chairman].get("provider_model")
            if not isinstance(provider_model, str) or not provider_model.strip():
                chairman_pool[chairman]["provider_model"] = specs["provider_model"]
            else:
                chairman_pool[chairman]["provider_model"] = provider_model.strip()

            params = chairman_pool[chairman].get("params")
            if not isinstance(params, dict):
                params = {}

            temperature = params.get("temperature")
            if not isinstance(temperature, (int, float)) or not(0 <= float(temperature) <= 2):
                temperature = specs["params"]["temperature"]
            params["temperature"] = float(temperature)
            chairman_pool[chairman]["params"] = params
    chairman_pool = {chairman:{"label":chairman_pool[chairman]["label"], 
    "provider":chairman_pool[chairman]["provider"],
    "provider_model":chairman_pool[chairman]["provider_model"],
    "params":chairman_pool[chairman]["params"],
    "cost_tier":chairman_pool[chairman]["cost_tier"]} for chairman in chairman_defaults.keys()}
    memory_dictionary["chairman_pool"] = chairman_pool
    
    chairman_ids = list(sorted(chairman_pool.keys()))
    default_chairman = chairman_ids[0] if len(chairman_ids) > 0 else None
    if default_chairman is None and len(model_ids) > 0:
        default_chairman = model_ids[0]

    chairman_active = memory.get("chairman_active")
    chairman_active = chairman_active.strip() if (isinstance(chairman_active, str) and chairman_active.strip() in chairman_ids) else default_chairman
    memory_dictionary["chairman_active"] = chairman_active

    role_model_stats = memory.get("role_model_stats")
    if not isinstance(role_model_stats, dict):
        role_model_stats = {}

    repaired_role_model = {}
    for role in ROLES:
        role_model = role_model_stats.get(role)
        if not isinstance(role_model, dict):
            role_model = {}
        repaired_role_model[role] = {model: repair_cell(role_model.get(model)) for model in model_ids}
    memory_dictionary["role_model_stats"] = repaired_role_model

    routing_policy = memory.get("routing_policy")
    if not isinstance(routing_policy, dict):
        routing_policy = {}
    routing_policy_dictionary = {}

    ucb_c = routing_policy.get("ucb_c")
    if not isinstance(ucb_c, (int, float)) or not(0.0 <= float(ucb_c) <= 1.0):
        ucb_c = 0.5
    ucb_c = float(ucb_c)
    routing_policy_dictionary["ucb_c"] = ucb_c

    cost_penalty = routing_policy.get("cost_penalty")
    if not isinstance(cost_penalty, (int, float)) or not(0.0 <= float(cost_penalty) <= 1.0):
        cost_penalty = 0.4
    cost_penalty = float(cost_penalty)
    routing_policy_dictionary["cost_penalty"] = cost_penalty
    memory_dictionary["routing_policy"] = routing_policy_dictionary

    exploration = memory.get("exploration")
    if not isinstance(exploration, dict):
        exploration = {}
    exploration_dictionary = {}
    
    warmup_runs = exploration.get("warmup_runs")
    if not isinstance(warmup_runs, (int, float)) or not(0 <= int(warmup_runs) <= 5):
        warmup_runs = 3
    exploration_dictionary["warmup_runs"] = int(warmup_runs)

    runs_completed = exploration.get("runs_completed")
    if not isinstance(runs_completed, (int, float)):
        runs_completed = 0
    exploration_dictionary["runs_completed"] = int(runs_completed)
    memory_dictionary["exploration"] = exploration_dictionary

    chairman_summary_store = memory.get("chairman_summary_store")
    if not isinstance(chairman_summary_store, dict):
        chairman_summary_store = {}
    chairman_summaries_dictionary = {}

    bootstrap = chairman_summary_store.get("bootstrap", {})
    if not isinstance(bootstrap, dict):
        bootstrap = {}
    bootstrap_dictionary = {}
    for model in model_ids:
        specs = bootstrap.get(model)
        if not isinstance(specs, dict):
            specs = {}
        bootstrap_dictionary[model] = specs
    chairman_summaries_dictionary["bootstrap"] = bootstrap_dictionary

    iterate = chairman_summary_store.get("iterate", {})
    if not isinstance(iterate, dict):
        iterate = {}
    chairman_summaries_dictionary["iterate"] = iterate
    memory_dictionary["chairman_summary_store"] = chairman_summaries_dictionary

    timeout_defaults = memory.get("timeout_defaults")
    if not isinstance(timeout_defaults, dict):
        timeout_defaults = {}
    timeout_defaults_dictionary = {}
    
    run_agents_timeout_s = timeout_defaults.get("run_agents_timeout_s")
    if not isinstance(run_agents_timeout_s, (int, float)) or not(300 <= run_agents_timeout_s <= 360):
        run_agents_timeout_s = 300
    timeout_defaults_dictionary["run_agents_timeout_s"] = int(run_agents_timeout_s)

    chairman_timeout_s = timeout_defaults.get("chairman_timeout_s")
    if not isinstance(chairman_timeout_s, (int, float)) or not(300 <= chairman_timeout_s <= 360):
        chairman_timeout_s = 360
    timeout_defaults_dictionary["chairman_timeout_s"] = int(chairman_timeout_s)
    memory_dictionary["timeout_defaults"] = timeout_defaults_dictionary

    directory_structure = memory.get("directory_structure")
    if not isinstance(directory_structure, dict):
        directory_structure = {}
    directory_structure_dictionary = {}

    base_path =  directory_structure.get("base_path")
    base_path = base_path.strip() if isinstance(base_path, str) else ""
    if base_path:
        base_path = Path(base_path).resolve()
    else:
        base_path = None
    if base_path is None or not base_path.is_absolute() or not base_path.exists() or not base_path.is_dir():
        base_path = root_path / "code"
    base_path.mkdir(parents=True, exist_ok=True)
    directory_structure_dictionary["base_path"] = str(base_path)
    
    for model_id in model_ids:
        current_model = directory_structure.get(model_id)
        if not isinstance(current_model, dict):
            current_model = {}
        model_dictionary = {}
        model_path = str(base_path / model_id)
        Path(model_path).mkdir(parents=True, exist_ok=True)
        model_dictionary["path"] = model_path
        model_dirs = current_model.get("dirs")
        if not isinstance(model_dirs, dict):
            model_dirs = {}
        model_dictionary["dirs"] = model_dirs
        model_files = current_model.get("files")
        if not isinstance(model_files, list):
            model_files = []
        model_dictionary["files"] = model_files
        directory_structure_dictionary[model_id] = model_dictionary
    memory_dictionary["directory_structure"] = directory_structure_dictionary

    default_final_model = "M1"
    final_model = memory.get("final_model")
    final_model = final_model.strip() if (isinstance(final_model, str) and final_model.strip() in model_ids) else default_final_model
    memory_dictionary["final_model"] = final_model

    chairman_edits = memory.get("chairman_edits")
    if not isinstance(chairman_edits, dict):
        chairman_edits = {}
    chairman_edits_dictionary = {}

    bootstrap = chairman_edits.get("bootstrap")
    if not isinstance(bootstrap, dict):
        bootstrap = {}
    bootstrap_dictionary = {}
    for model in model_ids:
        specs = bootstrap.get(model)
        if not isinstance(specs, dict):
            specs = {}
        bootstrap_dictionary[model] = specs
    chairman_edits_dictionary["bootstrap"] = bootstrap_dictionary

    iterate = chairman_edits.get("iterate", {})
    if not isinstance(iterate, dict):
        iterate = {}
    chairman_edits_dictionary["iterate"] = iterate
    memory_dictionary["chairman_edits"] = chairman_edits_dictionary
    
    return memory_dictionary

def load_memory_file(file_path: Path) -> Dict[str, Any] | None:

    memory_json = None
    file_path = str(file_path)
    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            memory_json = json.load(fh)
    except Exception:
        memory_json = None

    return memory_json

def write_memory(memory: Dict[str, Any], file_path: Path) -> bool:

    written = False
    file_path = str(file_path)
    try:
        with open(file_path, "w", encoding="utf-8") as fh:
            json.dump(memory, fh, indent=2, sort_keys=True)
        written = True
    except Exception:
        written = False

    return written

def load_or_create_memory(root: Path) -> Tuple[Dict[str, Any], bool]:

    memory_directory = root / "memory"
    memory_directory.mkdir(parents=True, exist_ok=True)

    memory_path = memory_directory / "memory.json"
    created_or_repaired = False     
    memory_json = load_memory_file(memory_path)
    first_run = False
    
    if memory_json is None:
        memory_json = {}
        created_or_repaired = True
        first_run = True

    repaired = repair_memory(memory_json, first_run, root)
    if repaired != memory_json:
        created_or_repaired = True
    
    if created_or_repaired:
        written = write_memory(repaired, memory_path)
        if not written:
            written = write_memory(repaired, memory_path)

    return (repaired, first_run)
                
def load_memory(state: Dict[str, Any]) -> Dict[str, Any]:

    print("------------------------------------------------------------------------")
    print("-------------------------Loading-Memory---------------------------------")
    print("------------------------------------------------------------------------")

    root = Path(os.getcwd()).resolve()
    memory, first_run = load_or_create_memory(root)

    return {"memory": memory, "root": str(root), "first_run": bool(first_run)}