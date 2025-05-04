from typing import Dict, Any, List, TypedDict, Optional

class GraphState(TypedDict, total=False):
    """State for the LangGraph pipeline."""
    feedback_modifications: Dict[str, str]
    nodes_to_rerun: List[str]
    selected_flights: List[Dict[str, Any]]
    hotel: Dict[str, Any]
    error: Optional[str]

def determine_nodes_to_rerun(category: int, feedback: str) -> List[str]:
    """
    Determine which nodes need to be rerun based on feedback category.
    
    Args:
        category: Feedback category number (1-6)
        feedback: User's feedback text
        
    Returns:
        List of node names that need to be rerun
    """
    if category == 1:  # Transportation
        return ["flights"] if "flight" in feedback.lower() else ["route"]
    elif category == 2:  # Accommodations
        return ["hotel"]
    elif category == 3:  # Activities/Places
        return ["places"]
    elif category == 4:  # Restaurants
        return ["restaurants"]
    elif category == 5:  # Schedule
        return ["summary"]  # Only need to adjust the schedule
    elif category == 6:  # Budget
        return ["budget", "summary"]
    return []

async def feedback_parser_node(state: GraphState, feedback: Dict[str, Any]) -> GraphState:
    """
    Interprets user feedback and updates state for replanning.
    
    Args:
        state: Current graph state
        feedback: Dictionary containing feedback category and text
        
    Returns:
        Updated state with feedback modifications and nodes to rerun
    """
    category = feedback["category"]
    feedback_text = feedback["feedback"]
    
    # Initialize feedback modifications in state if not present
    if "feedback_modifications" not in state:
        state["feedback_modifications"] = {}
    
    # Process based on category
    if category == 1:  # Transportation
        state["feedback_modifications"]["transportation"] = feedback_text
        # Clear selected flights if user wants different options
        if "selected_flights" in state:
            state["selected_flights"] = []
    
    elif category == 2:  # Accommodations
        state["feedback_modifications"]["hotel"] = feedback_text
        # Clear hotel to force regeneration
        if "hotel" in state:
            state["hotel"] = {}
    
    elif category == 3:  # Activities/Places
        state["feedback_modifications"]["places"] = feedback_text
        
    elif category == 4:  # Restaurants
        state["feedback_modifications"]["restaurants"] = feedback_text
        
    elif category == 5:  # Schedule
        state["feedback_modifications"]["schedule"] = feedback_text
        
    elif category == 6:  # Budget
        state["feedback_modifications"]["budget"] = feedback_text
    
    # Mark which nodes need to be rerun
    state["nodes_to_rerun"] = determine_nodes_to_rerun(category, feedback_text)
    
    return state 