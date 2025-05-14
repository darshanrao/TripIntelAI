from typing import Dict, Any, List
import os
import googlemaps
from app.utils.logger import logger
from app.schemas.trip_schema import TripMetadata
from app.nodes.agent_nodes import get_city_attractions, _get_restaurants, geocode_location

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
            
        # Check if the Google Places API key is loaded
        api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        if not api_key:
            logger.error("Google Places API key not found. Cannot initialize Google Maps client.")
            raise ValueError("Google Places API key not found")
        
        # Initialize Google Maps client
        gmaps = googlemaps.Client(key=api_key)
        
        # Geocode destination to get latitude and longitude
        city_lat, city_lng = geocode_location(destination, gmaps)
        if city_lat is None or city_lng is None:
            raise ValueError("Failed to geocode destination")
        
        # Get attractions using helper function
        attractions = get_city_attractions(city_lat, city_lng, destination)
        
        # Update state with attractions
        state["places"] = attractions
        
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
            
        # Check if the Google Places API key is loaded
        api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        if not api_key:
            logger.error("Google Places API key not found. Cannot initialize Google Maps client.")
            raise ValueError("Google Places API key not found")
        
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