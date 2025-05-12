from typing import Dict, Any, List
import os
import googlemaps
from app.utils.logger import logger
from app.schemas.trip_schema import TripMetadata

async def places_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get places (attractions and restaurants) for the destination.
    
    Args:
        state: Current state containing metadata and other information
        
    Returns:
        Updated state with places information
    """
    try:
        # Get metadata from state
        metadata = state.get("metadata")
        if not isinstance(metadata, TripMetadata):
            raise ValueError("Invalid metadata format")
            
        # Get destination from metadata
        destination = metadata.destination
        if not destination:
            raise ValueError("No destination specified in metadata")
            
        # Initialize Google Maps client
        gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API_KEY"))
        
        # Get preferences from metadata
        preferences = metadata.preferences or []
        
        # Search for places based on preferences
        places = []
        for preference in preferences:
            # Search for places matching the preference
            places_result = gmaps.places(
                query=f"{preference} in {destination}",
                type="tourist_attraction" if preference in ["museums", "historical sites"] else None
            )
            
            # Process results
            for place in places_result.get("results", []):
                place_details = {
                    "name": place.get("name"),
                    "place_id": place.get("place_id"),
                    "location": place.get("geometry", {}).get("location"),
                    "rating": place.get("rating"),
                    "types": place.get("types", []),
                    "category": preference
                }
                places.append(place_details)
        
        # Update state with places
        state["places"] = places
        
        return state
        
    except Exception as e:
        logger.error(f"Error in places node: {str(e)}")
        state["error"] = str(e)
        return state 