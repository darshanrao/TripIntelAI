from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime, timedelta
import random
import os
import requests
import googlemaps
from app.schemas.trip_schema import (
    Flight, Hotel, Place, Restaurant, Budget, TripMetadata
)

# Define GraphState for type hints
class GraphState(TypedDict, total=False):
    """State for the LangGraph pipeline."""
    metadata: Optional[TripMetadata]
    flights: List[Dict[str, Any]]
    route: Dict[str, Any]
    places: List[Dict[str, Any]]
    restaurants: List[Dict[str, Any]]
    hotel: Dict[str, Any]
    budget: Dict[str, Any]
    error: Optional[str]

# Helper function to generate mock data
def generate_mock_datetime(base_date: datetime, hour_offset: int) -> datetime:
    """Generate a mock datetime with the specified hour offset."""
    return base_date.replace(hour=hour_offset, minute=random.randint(0, 59))

# Initialize Google Maps client
def get_gmaps_client():
    """Get a Google Maps client instance with API key from environment."""
    api_key = os.environ.get("GOOGLE_PLACES_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_PLACES_API_KEY environment variable not set")
    return googlemaps.Client(key=api_key)

# Geocode a location name to latitude and longitude
def geocode_location(location_name, gmaps=None):
    """Convert a location name to latitude and longitude coordinates"""
    # Check cache first to avoid redundant API calls
    if hasattr(geocode_location, 'cache') and location_name in geocode_location.cache:
        return geocode_location.cache[location_name]
    
    # Initialize cache if it doesn't exist
    if not hasattr(geocode_location, 'cache'):
        geocode_location.cache = {}
    
    # Get or create Google Maps client
    if gmaps is None:
        gmaps = get_gmaps_client()
    
    try:
        # Use the geocoding API
        geocode_result = gmaps.geocode(location_name)
        
        if geocode_result and len(geocode_result) > 0:
            location = geocode_result[0]['geometry']['location']
            result = (location['lat'], location['lng'])
            
            # Cache the result
            geocode_location.cache[location_name] = result
            return result
        else:
            print(f"Could not geocode location: {location_name}")
            return None, None
            
    except Exception as e:
        print(f"Error geocoding location {location_name}: {e}")
        return None, None

def get_place_photo_url(photo_reference, max_width=400):
    """
    Generate a Google Places photo URL from a photo reference
    
    Args:
        photo_reference (str): The photo reference string from Google Places API
        max_width (int): Maximum width of the image in pixels
        
    Returns:
        str: URL to the Google Places photo
    """
    if not photo_reference:
        return None
        
    api_key = os.environ.get('GOOGLE_PLACES_API_KEY')
    if not api_key:
        print("GOOGLE_PLACES_API_KEY environment variable not set")
        return None
        
    return f"https://maps.googleapis.com/maps/api/place/photo?maxwidth={max_width}&photoreference={photo_reference}&key={api_key}"

def get_places(latitude, longitude, radius=25000, place_type=None, keyword=None):
    """
    Find places using Google Places API
    
    Parameters:
    - latitude: float - Latitude coordinate
    - longitude: float - Longitude coordinate
    - radius: int - Search radius in meters (default: 25000, max 50000)
    - place_type: str - Type of place to search for (e.g., "tourist_attraction", "museum")
    - keyword: str - Additional search keyword
    
    Returns:
    - list of place results
    """
    # Ensure radius doesn't exceed API limits
    if radius > 50000:
        print(f"Warning: Radius reduced from {radius}m to 50000m (API maximum)")
        radius = 50000
    
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    
    # Base parameters
    params = {
        "location": f"{latitude},{longitude}",
        "radius": radius,
        "key": os.environ.get("GOOGLE_PLACES_API_KEY")
    }
    
    # Add place type if provided
    if place_type:
        params["type"] = place_type
    
    # Add keyword if provided
    if keyword:
        params["keyword"] = keyword
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get('status') != 'OK':
            print(f"Error fetching places: {data.get('status')}")
            return []
            
        # Sort by rating (highest first)
        results = data.get('results', [])
        results.sort(key=lambda x: x.get('rating', 0), reverse=True)
        
        return results
    except Exception as e:
        print(f"Error fetching places: {e}")
        return [] 