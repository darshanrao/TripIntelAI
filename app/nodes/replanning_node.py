from typing import Dict, Any, List, TypedDict, Optional
from app.schemas.trip_schema import TripMetadata

class GraphState(TypedDict, total=False):
    """State for the LangGraph pipeline."""
    metadata: Optional[TripMetadata]
    feedback_modifications: Dict[str, str]
    nodes_to_call: List[str]
    nodes_to_rerun: List[str]
    replanning: bool
    error: Optional[str]

async def replanning_node(state: GraphState) -> GraphState:
    """
    Determines replanning strategy based on feedback.
    
    This node analyzes feedback modifications and updates the planning strategy,
    including which nodes need to be called and how the metadata might need
    to be adjusted.
    
    Args:
        state: Current graph state containing feedback modifications
        
    Returns:
        Updated state with replanning strategy
    """
    # Extract feedback modifications
    modifications = state.get("feedback_modifications", {})
    nodes_to_rerun = state.get("nodes_to_rerun", [])
    
    # Update metadata based on feedback if necessary
    if "transportation" in modifications:
        transport_feedback = modifications["transportation"].lower()
        
        # Handle transportation mode changes
        if "drive" in transport_feedback or "car" in transport_feedback:
            # Switch from flights to driving route
            if "nodes_to_call" in state and "flights" in state["nodes_to_call"]:
                state["nodes_to_call"].remove("flights")
                if "route" not in state["nodes_to_call"]:
                    state["nodes_to_call"].append("route")
        
        elif "flight" in transport_feedback:
            # Switch from driving to flights
            if "nodes_to_call" in state and "route" in state["nodes_to_call"]:
                state["nodes_to_call"].remove("route")
                if "flights" not in state["nodes_to_call"]:
                    state["nodes_to_call"].append("flights")
    
    # Handle accommodation changes
    if "hotel" in modifications:
        hotel_feedback = modifications["hotel"].lower()
        
        # Update metadata preferences if specific preferences mentioned
        if state.get("metadata") and hasattr(state["metadata"], "preferences"):
            if "luxury" in hotel_feedback:
                if "luxury_hotels" not in state["metadata"].preferences:
                    state["metadata"].preferences.append("luxury_hotels")
            elif "budget" in hotel_feedback:
                if "budget_friendly" not in state["metadata"].preferences:
                    state["metadata"].preferences.append("budget_friendly")
    
    # Handle activity/place changes
    if "places" in modifications:
        places_feedback = modifications["places"].lower()
        
        # Update metadata preferences for activities
        if state.get("metadata") and hasattr(state["metadata"], "preferences"):
            if "museum" in places_feedback:
                if "museums" not in state["metadata"].preferences:
                    state["metadata"].preferences.append("museums")
            elif "outdoor" in places_feedback:
                if "outdoor_activities" not in state["metadata"].preferences:
                    state["metadata"].preferences.append("outdoor_activities")
    
    # Handle restaurant changes
    if "restaurants" in modifications:
        food_feedback = modifications["restaurants"].lower()
        
        # Update metadata preferences for dining
        if state.get("metadata") and hasattr(state["metadata"], "preferences"):
            if "vegetarian" in food_feedback:
                if "vegetarian_food" not in state["metadata"].preferences:
                    state["metadata"].preferences.append("vegetarian_food")
            elif "local" in food_feedback:
                if "local_cuisine" not in state["metadata"].preferences:
                    state["metadata"].preferences.append("local_cuisine")
    
    # Handle budget changes
    if "budget" in modifications:
        budget_feedback = modifications["budget"].lower()
        
        # Update metadata preferences for budget
        if state.get("metadata") and hasattr(state["metadata"], "preferences"):
            if "cheaper" in budget_feedback or "lower" in budget_feedback:
                if "budget_friendly" not in state["metadata"].preferences:
                    state["metadata"].preferences.append("budget_friendly")
            elif "luxury" in budget_feedback or "high-end" in budget_feedback:
                if "luxury_experience" not in state["metadata"].preferences:
                    state["metadata"].preferences.append("luxury_experience")
    
    # Mark state as being replanned
    state["replanning"] = True
    
    return state 