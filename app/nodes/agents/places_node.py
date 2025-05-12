from typing import Dict, Any, List
import os
import googlemaps
from app.utils.logger import logger
from app.schemas.trip_schema import TripMetadata
from app.nodes.agent_nodes import get_city_attractions, _get_restaurants, geocode_location

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
            
        # Check if the Google Maps API key is loaded
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not api_key:
            logger.error("Google Maps API key not found. Cannot initialize Google Maps client.")
            raise ValueError("Google Maps API key not found")
        else:
            logger.info("Google Maps API key loaded successfully.")
        
        # Initialize Google Maps client
        gmaps = googlemaps.Client(key=api_key)
        
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

async def fetch_attractions(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get attractions for the destination.
    
    Args:
        state: Current state containing metadata and other information
        
    Returns:
        Updated state with attractions information
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
            
        # Check if the Google Maps API key is loaded
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not api_key:
            logger.error("Google Maps API key not found. Cannot initialize Google Maps client.")
            raise ValueError("Google Maps API key not found")
        
        # Initialize Google Maps client
        gmaps = googlemaps.Client(key=api_key)
        
        # Geocode destination to get latitude and longitude
        city_lat, city_lng = geocode_location(destination, gmaps)
        if city_lat is None or city_lng is None:
            raise ValueError("Failed to geocode destination")
        
        # Get attractions using helper function
        attractions = get_city_attractions(city_lat, city_lng, destination)
        
        # Update state with attractions
        state["attractions"] = attractions
        
        return state
        
    except Exception as e:
        logger.error(f"Error in fetch_attractions: {str(e)}")
        state["error"] = str(e)
        return state

async def fetch_restaurants(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get restaurants for the destination.
    
    Args:
        state: Current state containing metadata and other information
        
    Returns:
        Updated state with restaurants information
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
            
        # Check if the Google Maps API key is loaded
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not api_key:
            logger.error("Google Maps API key not found. Cannot initialize Google Maps client.")
            raise ValueError("Google Maps API key not found")
        
        # Initialize Google Maps client
        gmaps = googlemaps.Client(key=api_key)
        
        # Geocode destination to get latitude and longitude
        city_lat, city_lng = geocode_location(destination, gmaps)
        if city_lat is None or city_lng is None:
            raise ValueError("Failed to geocode destination")
        
        # Get restaurants using helper function
        restaurants = _get_restaurants(city_lat, city_lng)
        
        # Update state with restaurants
        state["restaurants"] = restaurants
        
        return state
        
    except Exception as e:
        logger.error(f"Error in fetch_restaurants: {str(e)}")
        state["error"] = str(e)
        return state 