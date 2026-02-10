from typing import Any, Dict, List, TypedDict

from langgraph.graph import StateGraph, END

from memory.store import load_memory
from task.state import normalize_task
from orchestration.prompts import load_prompts
from task.select import select_role_assignments
from orchestration.inputs import build_agent_inputs
from orchestration.runner import run_agents
from orchestration.chairman import chairman_merge
from orchestration.persist import update_files, update_directory_structure, write_memory

class DERState(TypedDict, total=False):

    root: str
    first_run: bool

    memory: Dict[str, Any]
    task: Dict[str, Any]

    prompts: Dict[str, str]
    role_assignments: Dict[str, Any] 

    agent_calls: List[Dict[str, Any]]
    agent_results: Dict[str, Any]

def build_der_graph() -> Any:

    graph = StateGraph(DERState)

    graph.add_node("load_memory", load_memory)
    graph.add_node("normalize_task", normalize_task)
    graph.add_node("load_prompts", load_prompts)
    graph.add_node("select_role_assignments", select_role_assignments)
    graph.add_node("build_agent_inputs", build_agent_inputs)
    graph.add_node("run_agents", run_agents)
    graph.add_node("chairman_merge", chairman_merge)
    graph.add_node("update_files", update_files)
    graph.add_node("update_directory_structure", update_directory_structure)
    graph.add_node("write_memory", write_memory)

    graph.set_entry_point("load_memory")
    graph.add_edge("load_memory", "normalize_task")
    graph.add_edge("normalize_task", "load_prompts")
    graph.add_edge("load_prompts", "select_role_assignments")
    graph.add_edge("select_role_assignments", "build_agent_inputs")
    graph.add_edge("build_agent_inputs", "run_agents")
    graph.add_edge("run_agents", "chairman_merge")
    graph.add_edge("chairman_merge", "update_files")
    graph.add_edge("update_files", "update_directory_structure")
    graph.add_edge("update_directory_structure", "write_memory")
    graph.add_edge("write_memory", END)

    return graph.compile()

if __name__ == "__main__":
    
    app = build_der_graph()
    initial_state: DERState = {}
    final_state = app.invoke(initial_state)

    print("Run complete.")
