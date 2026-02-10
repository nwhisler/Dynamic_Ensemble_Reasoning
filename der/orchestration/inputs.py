from copy import deepcopy
from pathlib import Path
from typing import Dict, Any, List

AGENTS = ["architect", "implementer"]
LANGUAGES = {"python", "c++", "java"}
PHASES = {"bootstrap", "iterate"}

def get_role_prompt(prompts: Dict[str, Any], role: str) -> str:
    
    prompt = prompts.get(role)
    prompt = prompt.strip() if isinstance(prompt, str) else ""
    
    return prompt

def build_agent_calls(
    active_agents: List[str],
    model_ids: List[str],
    prompts: Dict[str, Any],
    rules: str,
    task: Dict[str, Any],
    active_weights: Dict[str, float],
    phase: str,
    calibration_mode: bool, 
    chairman_summary_store: Dict[str, Any],
    role_assignments: Dict[str, str]
) -> List[Dict[str, Any]]:

    agent_calls: List[Dict[str, Any]] = []

    if not active_agents:
        return agent_calls

    if len(model_ids) == 0:
        model_ids = ["M1"]

    default_model_id = model_ids[0]

    if calibration_mode:
        model_summary = chairman_summary_store.get(phase)
        if not isinstance(model_summary, dict):
            model_summary = {}
        for role in active_agents:
            role_prompt = get_role_prompt(prompts, role)
            for model_id in model_ids:
                chairman_summary = model_summary.get(model_id)
                if not isinstance(chairman_summary, dict):
                    chairman_summary = {}
                agent_calls.append({
                    "call_id": f"{role}_{model_id}",
                    "agent_id": role,
                    "model_id": model_id,
                    "task": task,
                    "rules": rules,
                    "role_prompt": role_prompt,
                    "agent_weight": float(active_weights.get(role, 0.5)),
                    "chairman_summary": chairman_summary
                })
        
        return agent_calls

    for role in active_agents:
        model_id = role_assignments.get(role)
        if model_id not in model_ids:
            model_id = default_model_id

        role_prompt = get_role_prompt(prompts, role)
        chairman_summary = chairman_summary_store.get(phase)
        if not isinstance(chairman_summary, dict):
            chairman_summary = {}

        agent_calls.append({
            "call_id": f"{role}_{model_id}",
            "agent_id": role,
            "model_id": model_id,
            "task": task,
            "rules": rules,
            "role_prompt": role_prompt,
            "agent_weight": float(active_weights.get(role, 0.5)),
            "chairman_summary": chairman_summary
        })

    return agent_calls

def normalize_weights(weighted_inputs: Dict[str, Any], active_agents: List[str]) -> Dict[str, float]:

    if not isinstance(active_agents, list) or len(active_agents) == 0:
        return {}

    if not isinstance(weighted_inputs, dict):
        weighted_inputs = {}

    weighted_inputs = deepcopy(weighted_inputs)

    for role in active_agents:
        role_weight = weighted_inputs.get(role)
        if not isinstance(role_weight, (int, float)) or role_weight < 0:
            role_weight = 0.5
        weighted_inputs[role] = float(role_weight)
    weighted_inputs = {role:weighted_inputs[role] for role in active_agents}
    total = sum(weighted_inputs.values())

    if total <= 0.0:
        weighted_inputs = {role:(1/len(active_agents)) for role in active_agents}
    else:
        weighted_inputs = {role:(weighted_inputs[role]/total) for role in active_agents}
    
    return weighted_inputs

def build_agent_inputs(state: Dict[str, Any]) -> Dict[str, Any]:

    print("------------------------------------------------------------------------")
    print("-------------------------Building-Agent-Inputs--------------------------")
    print("------------------------------------------------------------------------")

    task = state.get("task")
    if not isinstance(task, dict):      
        task = {}

    phase = task.get("phase")
    phase = phase.strip().lower() if (isinstance(phase, str) and phase.strip().lower() in PHASES) else "bootstrap"
    
    calibration_mode = (phase == "bootstrap")

    memory = state.get("memory")
    if not isinstance(memory, dict):
        memory = {}

    weighted_inputs = memory.get("weighted_inputs")
    if not isinstance(weighted_inputs, dict):
        weighted_inputs = {}
    active_weights = normalize_weights(weighted_inputs, AGENTS[:])

    model_pool = memory.get("model_pool")
    if not isinstance(model_pool, dict):
        model_pool = {
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

    model_ids = list(sorted(model_pool.keys()))
    if len(model_ids) == 0:
        model_ids = ["M1"]

    prompts = state.get("prompts")
    if not isinstance(prompts, dict):
        prompts = {}

    rules = prompts.get("rules")
    rules = rules.strip() if isinstance(rules, str) else ""

    role_assignments = state.get("role_assignments")
    if not isinstance(role_assignments, dict):
        role_assignments = {}

    read_only_task = deepcopy(task)

    chairman_summary_store = memory.get("chairman_summary_store")
    if not isinstance(chairman_summary_store, dict):
        chairman_summary_store = {}

    agent_calls = build_agent_calls(
        active_agents=AGENTS[:],
        model_ids=model_ids,
        prompts=prompts,
        rules=rules,
        task=read_only_task,
        active_weights=active_weights,
        phase=phase,
        calibration_mode=calibration_mode,
        chairman_summary_store=chairman_summary_store,
        role_assignments=role_assignments
    )

    return {"agent_calls": agent_calls}