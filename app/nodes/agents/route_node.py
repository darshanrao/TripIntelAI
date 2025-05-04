from typing import Dict, Any, Optional
import random
from app.schemas.trip_schema import TripMetadata
from app.nodes.agents.common import GraphState

async def route_node(state: GraphState) -> GraphState:
    """
    Calculate route information for the trip.
    
    Args:
        state: Current state containing trip metadata
        
    Returns:
        Updated state with route information
    """
    metadata: Optional[TripMetadata] = state.get("metadata")
    
    if not metadata:
        state["route"] = {}
        return state
    
    # Mock route data
    distance_km = random.randint(50, 500)
    duration_hours = distance_km / 80  # Assuming average speed of 80 km/h
    
    route_info = {
        "distance_km": distance_km,
        "duration_hours": round(duration_hours, 1),
        "directions": f"Take the highway from {metadata.source} to {metadata.destination}",
        "map_url": f"https://maps.google.com/?saddr={metadata.source}&daddr={metadata.destination}"
    }
    
    # Add to state
    state["route"] = route_info
    
    return state 