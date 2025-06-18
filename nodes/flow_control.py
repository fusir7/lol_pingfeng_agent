from langgraph.graph import END
from nodes.types import GraphState

def decide_next_step(state: GraphState) -> str:
    """决定下一步操作"""
    if "error" in state and state["error"]:
        print(f"发生错误: {state['error']}")
        return END
    
    if "final_result" in state and state["final_result"]:
        return END
        
    return "continue" 