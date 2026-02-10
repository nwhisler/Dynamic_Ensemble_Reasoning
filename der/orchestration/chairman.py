import json
import math
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple
from utils.utils import is_within_base, load_output
from .runner import run_provider

PHASES = {"iterate", "bootstrap"}
ROLES = ["architect", "implementer"]
LANGUAGES = {"python", "java", "c++"}

def parse_chairman_output(chairman_output: Dict[str, Any]) -> Dict[str, Any]:

    if not isinstance(chairman_output, dict):
        return {}

    parsed_output: Dict[str, Any] = {}

    approved_edits = chairman_output.get("approved_edits")
    if not isinstance(approved_edits, list):
        approved_edits = []
    edits_list = []
    for edit in approved_edits:
        if isinstance(edit, dict):
            edits_dictionary = {}
            edit_keys = ["proposal_ids", "path", "content"]
            for key, value in edit.items():
                current_key = key.strip().lower() if isinstance(key, str) else ""
                if current_key in edit_keys:
                    if current_key == "proposal_ids":
                        if isinstance(value, list):
                            value = [string for string in value if isinstance(string, str)]
                            edits_dictionary[current_key] = value
                        else:
                            edits_dictionary[current_key] = []
                    elif current_key == "path":
                        value = value.strip() if isinstance(value, str) else ""
                        edits_dictionary[current_key] = value
                    elif current_key == "content":
                        value = value.strip() if isinstance(value, str) else ""
                        edits_dictionary[current_key] = value      
            edits_list.append(edits_dictionary)  
    parsed_output["approved_edits"] = edits_list    

    chairman_summary = chairman_output.get("chairman_summary")
    if not isinstance(chairman_summary, dict):
        chairman_summary = {}
    chairman_summary_dictionary = {}

    accepted_design_moves = chairman_summary.get("accepted_design_moves")
    if not isinstance(accepted_design_moves, list):
        accepted_design_moves = []
    accepted_list = []
    for move in accepted_design_moves:
        if isinstance(move, dict):
            accepted_dictionary = {}
            proposal_id = move.get("proposal_id")
            proposal_id = proposal_id.strip() if isinstance(proposal_id, str) else ""
            accepted_dictionary["proposal_id"] = proposal_id
            goal = move.get("goal")
            goal = goal.strip() if isinstance(goal, str) else ""
            accepted_dictionary["goal"] = goal
            accepted_list.append(accepted_dictionary)
    chairman_summary_dictionary["accepted_design_moves"] = accepted_list

    rejected_design_moves = chairman_summary.get("rejected_design_moves")
    if not isinstance(rejected_design_moves, list):
        rejected_design_moves = []
    rejected_list = []
    for move in rejected_design_moves:
        if isinstance(move, dict):
            rejected_dictionary = {}
            proposal_id = move.get("proposal_id")
            proposal_id = proposal_id.strip() if isinstance(proposal_id, str) else ""
            rejected_dictionary["proposal_id"] = proposal_id
            reason = move.get("reason")
            reason = reason.strip() if isinstance(reason, str) else ""
            rejected_dictionary["reason"] = reason
            rejected_list.append(rejected_dictionary)
    chairman_summary_dictionary["rejected_design_moves"] = rejected_list

    files_changed = chairman_summary.get("files_changed")
    if not isinstance(files_changed, list):
        files_changed = []
    files_changed = [string for string in files_changed if isinstance(string, str)]
    chairman_summary_dictionary["files_changed"] = files_changed

    files_created = chairman_summary.get("files_created")
    if not isinstance(files_created, list):
        files_created = []
    files_created = [string for string in files_created if isinstance(string, str)]
    chairman_summary_dictionary["files_created"] = files_created

    next_priorities = chairman_summary.get("next_priorities")
    if not isinstance(next_priorities, list):
        next_priorities = []
    next_priorities = [string for string in next_priorities if isinstance(string, str)]
    chairman_summary_dictionary["next_priorities"] = next_priorities

    added_design_moves = chairman_summary.get("added_design_moves")
    if not isinstance(added_design_moves, list):
        added_design_moves = []
    added_list = []
    for move in added_design_moves:
        if isinstance(move, dict):
            added_dictionary = {}
            proposal_id = move.get("proposal_id")
            proposal_id = proposal_id.strip() if isinstance(proposal_id, str) else ""
            added_dictionary["proposal_id"] = proposal_id
            goal = move.get("goal")
            goal = goal.strip() if isinstance(goal, str) else ""
            added_dictionary["goal"] = goal
            added_list.append(added_dictionary)
    chairman_summary_dictionary["added_design_moves"] = added_list
    parsed_output["chairman_summary"] = chairman_summary_dictionary

    scoring = chairman_output.get("scoring")
    if not isinstance(scoring, dict):
        scoring = {}
    scoring_dictionary = {}

    architect = scoring.get("architect")
    if not isinstance(architect, dict):
        architect = {}
    architect_dictionary = {}

    architect_judge_score = architect.get("judge_score")
    if not isinstance(architect_judge_score, (int, float)) or not(0.0 <= float(architect_judge_score) <= 1.0):
        architect_judge_score = 0.0
    architect_dictionary["judge_score"] = architect_judge_score

    architect_cost_score = architect.get("cost_score")
    if not isinstance(architect_cost_score, (int, float)) or not(0.0 <= float(architect_cost_score) <= 1.0):
        architect_cost_score = 0.5
    architect_dictionary["cost_score"] = architect_cost_score
    scoring_dictionary["architect"] = architect_dictionary

    implementer = scoring.get("implementer")
    if not isinstance(implementer, dict):
        implementer = {}
    implementer_dictionary = {}

    implementer_judge_score = implementer.get("judge_score")
    if not isinstance(implementer_judge_score, (int, float)) or not(0.0 <= float(implementer_judge_score) <= 1.0):
        implementer_judge_score = 0.0
    implementer_dictionary["judge_score"] = implementer_judge_score

    implementer_cost_score = implementer.get("cost_score")
    if not isinstance(implementer_cost_score, (int, float)) or not(0.0 <= float(implementer_cost_score) <= 1.0):
        implementer_cost_score = 0.5
    implementer_dictionary["cost_score"] = implementer_cost_score
    scoring_dictionary["implementer"] = implementer_dictionary

    parsed_output["scoring"] = scoring_dictionary

    return parsed_output   

def calculate_stats(model_stats: Dict[str, Any], total_runs: int, routing_policy: Dict[str, Any], scoring: Dict[str, Any]) -> Dict[str, Any]:

    updated_stats: Dict[str, Any] = {}

    n = model_stats.get("n", 0)
    if not isinstance(n , (int, float)):
        n = 0
    n = int(n)
    n_new = n + 1

    judge_score = scoring.get("judge_score", 0.0)
    if not isinstance(judge_score, (int, float)) or not(0.0 <= float(judge_score) <= 1.0):
        judge_score = 0.0
    judge_score = float(judge_score)

    mean_reward = model_stats.get("mean_reward", 0.0)
    if not isinstance(mean_reward, (int, float)) or not(0.0 <= float(mean_reward) <= 1.0):
        mean_reward = 0.0
    mean_reward = float(mean_reward)
    mean_reward_new = mean_reward + (judge_score - mean_reward) / n_new

    cost_score = scoring.get("cost_score", 0.5)
    if not isinstance(cost_score, (int, float)) or not(0.0 <= float(cost_score) <= 1.0):
        cost_score = 0.5
    cost_score = float(cost_score)

    mean_cost = model_stats.get("mean_cost", 0.0)
    if not isinstance(mean_cost, (int, float)) or not(0.0 <= float(mean_cost) <= 1.0):
        mean_cost = 0.0
    mean_cost = float(mean_cost)
    mean_cost_new = mean_cost + (cost_score - mean_cost) / n_new

    cost_penalty = routing_policy.get("cost_penalty", 0.4)
    if not isinstance(cost_penalty, (int, float)) or not(0.0 <= float(cost_penalty) <= 1.0):
        cost_penalty = 0.4
    cost_penalty = float(cost_penalty)

    ucb_c = routing_policy.get("ucb_c", 0.5)
    if not isinstance(ucb_c, (int, float)) or not(0.0 <= float(ucb_c) <= 1.0):
        ucb_c = 0.5
    ucb_c = float(ucb_c)

    ucb = mean_reward_new - cost_penalty * mean_cost_new + ucb_c * math.sqrt(math.log(max(total_runs, 2)) / max(n_new, 1))

    updated_stats["n"] = n_new
    updated_stats["mean_reward"] = mean_reward_new
    updated_stats["mean_cost"] = mean_cost_new
    updated_stats["last_used_run_id"] = model_stats.get("last_used_run_id")
    updated_stats["ucb"] = ucb

    return updated_stats

def generate_module_comparison(output: Dict[str, Any], base_path: Path) -> Dict[str, Any]:

    if not isinstance(output, dict):
        return {}

    modules = output.get("modules_added_and_updated")
    if not isinstance(modules, list):
        modules = []
    modules_list = []
    for module in modules:
        if isinstance(module, dict):
            module_dictionary = {}
            proposal_ids = module.get("proposal_ids")
            if isinstance(proposal_ids, list):
                proposal_ids = [string for string in proposal_ids if isinstance(string, str)]
                module_dictionary["proposal_ids"] = proposal_ids
            else:
                module_dictionary["proposal_ids"] = []
            path = module.get("path")
            path = path.strip() if isinstance(path, str) else ""
            if not path:
                continue
            path = Path(path).resolve()
            if not is_within_base(path, base_path):
                continue
            module_dictionary["path"] = str(path)
            current_module_content = ""
            if path.exists():
                current_module_content = path.read_text(encoding="utf-8")  
            module_dictionary["current_module_content"] = current_module_content
            updated_module_content = module.get("content")
            updated_module_content = updated_module_content.strip() if isinstance(updated_module_content, str) else ""
            module_dictionary["updated_module_content"] = updated_module_content
            modules_list.append(module_dictionary)
    
    return {"proposed_updates": modules_list} 

def chairman_merge(state: Dict[str, Any]) -> Dict[str, Any]:

    print("------------------------------------------------------------------------")
    print("-------------------------Calling-Chairman-------------------------------")
    print("------------------------------------------------------------------------")

    agent_results = state.get("agent_results")
    if not isinstance(agent_results, dict):
        agent_results = {}

    agent_calls = state.get("agent_calls")
    if not isinstance(agent_calls, list):
        agent_calls = []

    role_assignments = state.get("role_assignments")
    if not isinstance(role_assignments, dict):
        role_assignments = {}
    
    task = state.get("task")
    if not isinstance(task, dict):
        task = {}
    
    task_json = json.dumps(task, sort_keys=True, separators=(",", ":"))

    language = task.get("language", "python")
    language = language.strip().lower() if (isinstance(language, str) and language.strip().lower() in LANGUAGES) else "python"

    phase = task.get("phase")
    phase = phase.strip().lower() if (isinstance(phase, str) and phase.strip().lower() in PHASES) else "bootstrap"

    prompts = state.get("prompts")
    if not isinstance(prompts, dict):
        prompts = {}

    rules = prompts.get("rules")
    rules = rules.strip() if isinstance(rules, str) else ""

    chairman_prompt = prompts.get("chairman")
    chairman_prompt = chairman_prompt.strip() if isinstance(chairman_prompt, str) else ""

    memory = state.get("memory")
    if not isinstance(memory, dict):
        memory = {}

    model_pool = memory.get("model_pool")
    if not isinstance(model_pool, dict):
        model_pool = {}

    model_ids = list(sorted(model_pool.keys()))

    role_model_stats = memory.get("role_model_stats")
    if not isinstance(role_model_stats, dict):
        role_model_stats = {}

    routing_policy = memory.get("routing_policy")
    if not isinstance(routing_policy, dict):
        routing_policy = {}

    chairman_pool = memory.get("chairman_pool")
    if not isinstance(chairman_pool, dict):
        chairman_pool = {}

    chairman_ids = list(sorted(chairman_pool.keys()))

    chairman_active = memory.get("chairman_active")
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

    chairman_summary_store = memory.get("chairman_summary_store")
    if not isinstance(chairman_summary_store, dict):
        chairman_summary_store = {}
    chairman_summary_store_dictionary = {}

    summary_bootstrap = chairman_summary_store.get("bootstrap")
    if not isinstance(summary_bootstrap, dict):
        summary_bootstrap = {}
    summary_bootstrap_dictionary = {}
    for model in model_ids:
        current_model = summary_bootstrap.get(model)
        if isinstance(current_model, dict):
            summary_bootstrap_dictionary[model] = current_model
        else:
            summary_bootstrap_dictionary[model] = {}
    chairman_summary_store_dictionary["bootstrap"] = summary_bootstrap_dictionary

    summary_iterate = chairman_summary_store.get("iterate")
    if not isinstance(summary_iterate, dict):
        summary_iterate = {}
    chairman_summary_store_dictionary["iterate"] = summary_iterate
    chairman_summary_store = chairman_summary_store_dictionary

    timeout_defaults = memory.get("timeout_defaults")
    if not isinstance(timeout_defaults, dict):
        timeout_defaults = {}

    chairman_timeout_s = timeout_defaults.get("chairman_timeout_s")
    if not isinstance(chairman_timeout_s, (int, float)) or not (300 <= int(chairman_timeout_s) <= 360):
        chairman_timeout_s = 360
    chairman_timeout_s = int(chairman_timeout_s)
    
    run_id = memory.get("current_run_id")
    run_id = run_id.strip() if isinstance(run_id, str) else ""

    directory_structure = memory.get("directory_structure")
    if not isinstance(directory_structure, dict):
        directory_structure = {}

    final_model = memory.get("final_model")
    final_model = final_model.strip() if isinstance(final_model, str) else ""

    chairman_edits = memory.get("chairman_edits")
    if not isinstance(chairman_edits, dict):
        chairman_edits = {}
    chairman_edits_dictionary = {}

    chairman_edits_bootstrap = chairman_edits.get("bootstrap")
    if not isinstance(chairman_edits_bootstrap, dict):
        chairman_edits_bootstrap = {}
    chairman_edits_bootstrap_dictionary = {}
    for model in model_ids:
        current_model = chairman_edits_bootstrap.get(model)
        if isinstance(current_model, dict):
            chairman_edits_bootstrap_dictionary[model] = current_model
        else:
            chairman_edits_bootstrap_dictionary[model] = {}
    chairman_edits_dictionary["bootstrap"] = chairman_edits_bootstrap_dictionary

    chairman_edits_iterate = chairman_edits.get("iterate")
    if not isinstance(chairman_edits_iterate, dict):
        chairman_edits_iterate = {}
    chairman_edits_dictionary["iterate"] = chairman_edits_iterate
    chairman_edits = chairman_edits_dictionary

    system_text = f"{rules}\n\n{chairman_prompt}".strip()

    if phase == "bootstrap":
        for model_id in model_ids:
            user_text = f"TASK_JSON:\n{task_json}\n\n"
            code_directory = directory_structure.get(model_id)
            if not isinstance(code_directory, dict):
                code_directory = {}
            base_path = code_directory.get("path")
            if isinstance(base_path, str) and base_path.strip():
                base_path = Path(base_path.strip()).resolve()
            else:
                base_path = Path(os.getcwd()).resolve() / "code" / str(model_id)
                base_path.mkdir(parents=True, exist_ok=True)
            code_directory_json = json.dumps(code_directory, sort_keys=True, separators=(",", ":"))
            user_text += f"DIRECTORY_STRUCTURE_JSON:\n{code_directory_json}\n\n"
            for role in ROLES:
                call_id = f"{role}_{model_id}"
                result = agent_results.get(call_id)
                if not isinstance(result, dict):
                    result = {}
                output = result.get("output")
                if not isinstance(output, dict):
                    output = {}
                if role == "architect":
                    architect_output_json = json.dumps(output, sort_keys=True, separators=(",", ":"))
                    user_text += f"ARCHITECT_OUTPUT_JSON:\n{architect_output_json}\n\n"
                elif role == "implementer":
                    module_comparison = generate_module_comparison(output, base_path)
                    module_comparison_json = json.dumps(module_comparison, sort_keys=True, separators=(",", ":"))
                    user_text += f"MODULE_COMPARISON_JSON:\n{module_comparison_json}\n"

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
            if not isinstance(loaded_chairman_output, dict):
                loaded_chairman_output = {}
            parsed_chairman_output = parse_chairman_output(loaded_chairman_output)
            if parsed_chairman_output:
                chairman_scoring = parsed_chairman_output.get("scoring")
                if not isinstance(chairman_scoring, dict):
                    chairman_scoring = {}
                for role in ROLES:
                    role_models = role_model_stats.get(role)
                    if not isinstance(role_models, dict):
                        role_models = {}
                    role_model = role_models.get(model_id)
                    if not isinstance(role_model, dict):
                        role_model = {}
                    role_model["last_used_run_id"] = run_id
                    total_runs = sum(int(model.get("n", 0)) for model in role_models.values() if isinstance(model, dict) and isinstance(model.get("n", 0), (int, float))) + 1
                    role_scoring = chairman_scoring.get(role)
                    if not isinstance(role_scoring, dict):
                        role_scoring = {}
                    updated_model_stats = calculate_stats(role_model, total_runs, routing_policy, role_scoring)
                    role_model_stats.setdefault(role, {})
                    role_model_stats[role][model_id] = updated_model_stats
            
            chairman_summary = parsed_chairman_output.get("chairman_summary")
            if not isinstance(chairman_summary, dict):
                chairman_summary = {}
            chairman_summary_store[phase][model_id] = chairman_summary
            memory["chairman_summary_store"] = chairman_summary_store

            approved_edits = parsed_chairman_output.get("approved_edits")
            if not isinstance(approved_edits, list):
                approved_edits = []
            chairman_edits[phase][model_id] = {"approved_edits": approved_edits}
            memory["chairman_edits"]= chairman_edits

    elif phase == "iterate":
        user_text = f"TASK_JSON:\n{task_json}\n\n"
        architect_output = {}
        implementer_output = {}
        code_directory = directory_structure.get(final_model)
        if not isinstance(code_directory, dict):
            code_directory = {}
        base_path = code_directory.get("path")
        if isinstance(base_path, str) and base_path.strip():
            base_path = Path(base_path.strip()).resolve()
        else:
            base_path = Path(os.getcwd()).resolve() / "code" / str(final_model)
            base_path.mkdir(parents=True, exist_ok=True)
        for role in ROLES:
            model_id = role_assignments.get(role)
            model_id = model_id.strip() if isinstance(model_id, str) else ""
            call_id = f"{role}_{model_id}"
            result = agent_results.get(call_id)
            if not isinstance(result, dict):
                result = {}
            output = result.get("output")
            if not isinstance(output, dict):
                output = {}
            if role == "architect":
                architect_output = output
            elif role == "implementer":
                implementer_output = output

        code_directory_json = json.dumps(code_directory, sort_keys=True, separators=(",", ":"))     
        architect_output_json = json.dumps(architect_output, sort_keys=True, separators=(",", ":"))  
        module_comparison = generate_module_comparison(implementer_output, base_path)
        module_comparison_json = json.dumps(module_comparison, sort_keys=True, separators=(",", ":"))
            
        user_text += (
                        f"DIRECTORY_STRUCTURE_JSON:\n{code_directory_json}\n\n"
                        f"ARCHITECT_OUTPUT_JSON:\n{architect_output_json}\n\n"
                        f"MODULE_COMPARISON_JSON:\n{module_comparison_json}\n"
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
        if not isinstance(loaded_chairman_output, dict):
            loaded_chairman_output = {}
        parsed_chairman_output = parse_chairman_output(loaded_chairman_output)
        if parsed_chairman_output:
            chairman_scoring = parsed_chairman_output.get("scoring")
            if not isinstance(chairman_scoring, dict):
                chairman_scoring = {}
            for role in ROLES:
                model_id = role_assignments.get(role)
                model_id = model_id.strip() if isinstance(model_id, str) else ""
                role_models = role_model_stats.get(role)
                if not isinstance(role_models, dict):
                    role_models = {}
                role_model = role_models.get(model_id)
                if not isinstance(role_model, dict):
                    role_model = {}
                role_model["last_used_run_id"] = run_id
                total_runs = sum(int(model.get("n", 0)) for model in role_models.values() if isinstance(model, dict) and isinstance(model.get("n", 0), (int, float))) + 1
                role_scoring = chairman_scoring.get(role)
                if not isinstance(role_scoring, dict):
                    role_scoring = {}
                updated_model_stats = calculate_stats(role_model, total_runs, routing_policy, role_scoring)
                role_model_stats.setdefault(role, {})
                role_model_stats[role][model_id] = updated_model_stats
        
        chairman_summary = parsed_chairman_output.get("chairman_summary")
        if not isinstance(chairman_summary, dict):
            chairman_summary = {}
        chairman_summary_store[phase] = chairman_summary
        memory["chairman_summary_store"] = chairman_summary_store

        approved_edits = parsed_chairman_output.get("approved_edits")
        if not isinstance(approved_edits, list):
            approved_edits = []
        chairman_edits[phase] = {"approved_edits": approved_edits}
        memory["chairman_edits"] = chairman_edits
    memory["role_model_stats"] = role_model_stats 

    return {"memory": memory}


            









    




                        

            
