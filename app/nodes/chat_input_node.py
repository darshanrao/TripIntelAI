from typing import Dict, Any, TypedDict, Annotated
from langgraph.graph import StateGraph

# Define state type
class State(TypedDict):
    query: str
    raw_query: str

# Function-based implementation instead of class-based Node
async def chat_input_node(state: State) -> Dict[str, Any]:
    """
    Process the user's natural language input and add it to the state.
    
    Args:
        state: Current state containing the user's query
        
    Returns:
        Updated state with user query
    """
    # Extract user query from state
    user_query = state.get("query", "")
    
    # Add raw query to state
    state["raw_query"] = user_query
    
    return state
 