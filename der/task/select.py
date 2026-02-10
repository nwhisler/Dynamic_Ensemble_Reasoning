import numpy as np
from typing import Dict, Any, List

AGENTS = ["architect", "implementer"]
PHASES = {"bootstrap", "iterate"}

def select_role_assignments(state: Dict[str, Any]) -> Dict[str, Any]:

    print("------------------------------------------------------------------------")
    print("-------------------------Assigning-Roles--------------------------------")
    print("------------------------------------------------------------------------")

    role_assignments: Dict[str, Any] = {}

    task = state.get("task")
    if not isinstance(task, dict):
        task = {}

    phase = task.get("phase")
    phase = phase.strip().lower() if (isinstance(phase, str) and phase.strip().lower() in PHASES) else "bootstrap"

    if phase == "bootstrap":
        return {"role_assignments": {}}

    elif phase == "iterate":

        memory = state.get("memory")
        if not isinstance(memory, dict):
            memory = {}

        role_model_stats = memory.get("role_model_stats")
        if not isinstance(role_model_stats, dict):
            role_model_stats = {}

        roles = [role for role in AGENTS if role in role_model_stats]

        for role in roles:
            model_stats = role_model_stats[role]
            models = sorted(model_stats.keys())
            if not models:
                continue
            ucb_list = []
            for model in models:
                stats = model_stats[model]
                ucb = stats.get("ucb")
                if not isinstance(ucb, (int, float)):
                    ucb = 0.0
                ucb = float(ucb)
                ucb_list.append(ucb)
            model_idx = int(np.argmax(ucb_list))
            best_model = models[model_idx]
            role_assignments[role] = best_model
        
    return {"role_assignments": role_assignments}