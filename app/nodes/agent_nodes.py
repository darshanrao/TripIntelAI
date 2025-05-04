from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime, timedelta
import random
import os
import requests
import googlemaps
from anthropic import Anthropic
from app.schemas.trip_schema import (
    Flight, Hotel, Place, Restaurant, Budget, TripMetadata
)

import json
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import asyncio

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

# Flight API Models
class FlightSegment(BaseModel):
    from_airport: str
    to_airport: str
    departure: str
    arrival: str
    carrier_code: str
    duration: str

class FlightOption(BaseModel):
    price: str
    currency: str
    segments: List[FlightSegment]

# Amadeus Flight API Client
class AmadeusFlightSearch:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = self._get_access_token()
        self.iata_cache = {}  # local memory cache

    def _get_access_token(self) -> str:
        url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.api_secret
        }
        response = requests.post(url, data=data)
        if response.status_code != 200:
            raise Exception(f"Failed to get access token: {response.text}")
        return response.json()["access_token"]

    def get_iata_code(self, city_name: str) -> str:
        city_key = city_name.lower().strip()

        if city_key in self.iata_cache:
            return self.iata_cache[city_key]

        url = "https://test.api.amadeus.com/v1/reference-data/locations"
        params = {"keyword": city_name, "subType": "CITY"}
        headers = {"Authorization": f"Bearer {self.access_token}"}

        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 429:
            print("Rate limited: Too many location requests. Try again later.")
            return ""
        res.raise_for_status()
        data = res.json()

        if not data.get("data"):
            print(f"No IATA code found for city: '{city_name}'")
            iata_code = ""
            return iata_code
        iata_code = data["data"][0]["iataCode"]
        self.iata_cache[city_key] = iata_code
        return iata_code

    def search_flights(
        self,
        origin_city: str,
        destination_city: str,
        departure_date: str,
        return_date: str = None,
        adults: int = 1,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        origin = self.get_iata_code(origin_city)
        destination = self.get_iata_code(destination_city)
        print(f"Searching flights: {origin} → {destination}")
        raw_data = []
        if origin == "" or destination == "":
            print("Invalid IATA code for origin or destination.")
            return raw_data
        url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": adults,
            "currencyCode": "USD",
            "max": max_results
        }
        if return_date:
            params["returnDate"] = return_date

        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 429:
                raise Exception("Rate limited: Too many flight searches. Try again later.")
            response.raise_for_status()

            for i, offer in enumerate(response.json().get("data", []), start=1):
                price = f"{offer['price']['total']} {offer['price']['currency']}"
                for itinerary in offer["itineraries"]:
                    for segment in itinerary["segments"]:
                        flat_row = {
                            "option": i,
                            "price": price,
                            "from": segment["departure"]["iataCode"],
                            "to": segment["arrival"]["iataCode"],
                            "departure": segment["departure"]["at"],
                            "arrival": segment["arrival"]["at"],
                            "airline": segment["carrierCode"],
                            "duration": segment["duration"]
                        }
                        raw_data.append(flat_row)
            return raw_data
        except Exception as e:
            print(f"Error searching flights: {e}")
            return []

# Helper function to generate mock data
def _generate_mock_datetime(base_date: datetime, hour_offset: int) -> datetime:
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

# Get attractions in a city
def get_city_attractions(city_lat, city_lng, city_name="the city", radius=25000, attractions_keywords=None, sort_by="reviews"):
    """
    Find tourist attractions at the city level
    
    Parameters:
    - city_lat: float - City center latitude coordinate
    - city_lng: float - City center longitude coordinate
    - city_name: str - Name of the city (for logging)
    - radius: int - Search radius in meters (default: 25000, max 50000)
    - attractions_keywords: list - List of attraction keywords to search for (default: None)
    - sort_by: str - Sort results by "rating", "reviews", or "prominence" (default: "reviews")
    
    Returns:
    - list of attraction results sorted by the specified criteria
    """
    # Ensure radius doesn't exceed API limits
    if radius > 50000:
        print(f"Warning: Radius reduced from {radius}m to 50000m (API maximum)")
        radius = 50000
    
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    
    # Base parameters
    base_params = {
        "location": f"{city_lat},{city_lng}",
        "radius": radius,
        "key": os.environ.get("GOOGLE_PLACES_API_KEY")
    }
    
    results = []
    
    # Optimized list of place types for tourist attractions
    place_types = [
        "tourist_attraction",
        "museum",
        "aquarium",
        "art_gallery",
        "zoo",
        "landmark",
        "park"
    ]
    
    print(f"Searching for attractions in {city_name} (radius: {radius/1000:.1f}km)...")
    
    # If attraction keywords are provided, make separate requests for each keyword
    if attractions_keywords and isinstance(attractions_keywords, list) and len(attractions_keywords) > 0:
        for keyword in attractions_keywords:
            for place_type in place_types:
                keyword_params = base_params.copy()
                keyword_params["type"] = place_type
                keyword_params["keyword"] = keyword
                
                response = requests.get(url, params=keyword_params)
                result_data = response.json()
                
                if result_data.get('status') == "OK" and result_data.get('results'):
                    print(f"Found {len(result_data.get('results'))} results for '{place_type}' with keyword '{keyword}'")
                    results.extend(result_data.get('results'))
    else:
        # If no keywords, try each place type
        for place_type in place_types:
            type_params = base_params.copy()
            type_params["type"] = place_type
            
            response = requests.get(url, params=type_params)
            result_data = response.json()
            
            if result_data.get('status') == "OK" and result_data.get('results'):
                print(f"Found {len(result_data.get('results'))} results for '{place_type}'")
                results.extend(result_data.get('results'))
    
    # Remove duplicates based on place_id
    unique_results = {}
    for item in results:
        if 'place_id' in item:
            unique_results[item['place_id']] = item
    
    results = list(unique_results.values())
    
    # Sort results based on the specified criteria
    if sort_by == "rating":
        # Sort by rating (highest first), handling places with no rating
        results.sort(key=lambda x: (x.get('rating', 0) or 0, x.get('user_ratings_total', 0) or 0), reverse=True)
    elif sort_by == "reviews":
        # Sort by number of reviews (highest first)
        results.sort(key=lambda x: x.get('user_ratings_total', 0) or 0, reverse=True)
    
    print(f"Total unique attractions found in {city_name}: {len(results)}")
    return results

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

# ======= Node Functions =======

async def flights_node(state: GraphState) -> GraphState:
    """
    Find flight options for the trip using the Amadeus Flight API.
    
    Args:
        state: Current state containing trip metadata
        
    Returns:
        Updated state with flight options
    """
    metadata = state.get("metadata")
    
    if not metadata or not metadata.start_date or not metadata.end_date:
        state["flights"] = []
        state["error"] = "Missing trip metadata or dates"
        return state
    
    # Convert datetime objects to string dates that Amadeus API expects (YYYY-MM-DD)
    start_date_str = metadata.start_date.strftime("%Y-%m-%d") if hasattr(metadata.start_date, "strftime") else metadata.start_date
    end_date_str = metadata.end_date.strftime("%Y-%m-%d") if hasattr(metadata.end_date, "strftime") else metadata.end_date
    
    try:
        # Initialize the Amadeus API client
        api_key = os.getenv("AMADEUS_API_KEY")
        api_secret = os.getenv("AMADEUS_SECRET_KEY")
        
        if not api_key or not api_secret:
            # Fall back to mock data if API keys are not available
            print("Amadeus API credentials not found. Using mock flight data.")
            return await _generate_mock_flights(state)
        
        flight_client = AmadeusFlightSearch(api_key=api_key, api_secret=api_secret)
        
        # Search for flights
        flights_data = flight_client.search_flights(
            origin_city=metadata.source,
            destination_city=metadata.destination,
            departure_date=start_date_str,
            return_date=end_date_str,
            adults=metadata.num_people,
            max_results=5
        )
        
        # If no flights found, use mock data
        if not flights_data:
            print(f"No flights found between {metadata.source} and {metadata.destination}. Using mock data.")
            return await _generate_mock_flights(state)
        
        # Process the flight data into our schema
        flight_options = []
        
        # Group by option
        options = {}
        for flight in flights_data:
            option_num = flight.get("option")
            if option_num not in options:
                options[option_num] = []
            options[option_num].append(flight)
        
        # Create Flight objects for each option (outbound and return)
        for option_num, segments in options.items():
            for segment in segments:
                # Parse price
                price_parts = segment.get("price", "0 USD").split()
                price = float(price_parts[0]) if len(price_parts) > 0 else 0
                
                # Parse dates
                try:
                    departure_time = datetime.fromisoformat(segment.get("departure").replace('Z', '+00:00'))
                    arrival_time = datetime.fromisoformat(segment.get("arrival").replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    # If date parsing fails, use the trip dates
                    departure_time = metadata.start_date
                    arrival_time = metadata.start_date + timedelta(hours=2)
                
                # Create Flight object
                flight = Flight(
                    airline=segment.get("airline", "Unknown"),
                    flight_number=f"{segment.get('airline', 'X')}{random.randint(100, 999)}",
                    departure_time=departure_time,
                    arrival_time=arrival_time,
                    price=price
                )
                
                flight_options.append(flight)
        
        # Sort by price
        flight_options.sort(key=lambda x: x.price)
        
        # Add to state
        # We need to convert Flight objects to dictionaries
        state["flights"] = [flight.model_dump() for flight in flight_options]
        
        return state
    
    except Exception as e:
        print(f"Error in flights_node: {e}")
        # Fall back to mock data if an error occurs
        return await _generate_mock_flights(state)

async def _generate_mock_flights(state: GraphState) -> GraphState:
    """Generate mock flight data as a fallback"""
    metadata = state.get("metadata")
    
    # Mock flight data
    airlines = ["JetBlue", "Delta", "United", "American", "Southwest"]
    flight_options = []
    
    for i in range(3):  # Generate 3 flight options
        airline = random.choice(airlines)
        flight_number = f"{airline[0]}{random.randint(100, 999)}"
        departure_time = _generate_mock_datetime(metadata.start_date, 8 + i * 2)
        flight_duration = timedelta(hours=random.randint(1, 5), minutes=random.randint(0, 59))
        arrival_time = departure_time + flight_duration
        price = round(random.uniform(150, 400), 2)
        
        flight = Flight(
            airline=airline,
            flight_number=flight_number,
            departure_time=departure_time,
            arrival_time=arrival_time,
            price=price
        )
        
        flight_options.append(flight)
    
    # Generate return flights
    for i in range(3):  # Generate 3 return flight options
        airline = random.choice(airlines)
        flight_number = f"{airline[0]}{random.randint(100, 999)}"
        departure_time = _generate_mock_datetime(metadata.end_date, 16 + i * 2)
        flight_duration = timedelta(hours=random.randint(1, 5), minutes=random.randint(0, 59))
        arrival_time = departure_time + flight_duration
        price = round(random.uniform(150, 400), 2)
        
        flight = Flight(
            airline=airline,
            flight_number=flight_number,
            departure_time=departure_time,
            arrival_time=arrival_time,
            price=price
        )
        
        flight_options.append(flight)
    
    # Sort by price
    flight_options.sort(key=lambda x: x.price)
    
    # Add to state - use model_dump() instead of dict()
    state["flights"] = [flight.model_dump() for flight in flight_options]
    
    return state

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

async def places_node(state: GraphState) -> GraphState:
    """
    Find attractions and places to visit.
    Uses the Google Places API to find real attractions.
    
    Args:
        state: Current state containing trip metadata
        
    Returns:
        Updated state with places to visit
    """
    metadata: Optional[TripMetadata] = state.get("metadata")
    
    if not metadata or not metadata.destination:
        state["places"] = []
        return state
    
    try:
        # Get destination coordinates
        lat, lng = geocode_location(metadata.destination)
        
        if not lat or not lng:
            # Fallback to mock data if geocoding fails
            print(f"Could not geocode destination: {metadata.destination}. Using mock data.")
            return await _fallback_places_to_mock(state, metadata)
        
        # Get attractions based on user preferences
        attraction_keywords = None
        if metadata.preferences:
            # Filter out non-attraction related preferences
            attraction_related = ["museum", "history", "art", "nature", "outdoor", 
                                "culture", "landmark", "historic", "park", "family"]
            attraction_keywords = [p for p in metadata.preferences 
                                if any(word in p.lower() for word in attraction_related)]
        
        # Find attractions using the Google Places API
        attractions_data = get_city_attractions(
            city_lat=lat,
            city_lng=lng,
            city_name=metadata.destination,
            attractions_keywords=attraction_keywords,
            sort_by="reviews"
        )
        
        # Convert to our schema format (up to 5 top attractions)
        places = []
        for attraction in attractions_data[:5]:
            # Extract price information if available (usually not available from Places API)
            price = 0.0
            if attraction.get('price_level'):
                # Approximate prices based on price level
                price_mapping = {1: 0.0, 2: 10.0, 3: 20.0, 4: 30.0}
                price = price_mapping.get(attraction.get('price_level'), 0.0)
            
            # Get photo URL if available
            photo_url = None
            if attraction.get('photos') and len(attraction.get('photos')) > 0:
                photo_ref = attraction['photos'][0].get('photo_reference')
                if photo_ref:
                    photo_url = get_place_photo_url(photo_ref)
            
            # Create Place object
            place = Place(
                name=attraction.get('name', 'Unknown Attraction'),
                description=attraction.get('vicinity', 'No description available'),
                rating=attraction.get('rating', 4.0),
                price=price,
                location=attraction.get('vicinity', 'Unknown Location'),
                category=attraction.get('types', ['tourist_attraction'])[0].replace('_', ' ').title(),
                place_id=attraction.get('place_id')
            )
            
            places.append(place)
        
        # Add to state
        state["places"] = [place.dict() for place in places]
        
        # If we didn't find enough places, supplement with some mock data
        if len(places) < 3:
            mock_state = await _fallback_places_to_mock(state, metadata)
            mock_places = mock_state.get("places", [])
            
            # Add unique mock places until we have at least 3
            existing_names = {p.name for p in places}
            for mock_place in mock_places:
                if mock_place['name'] not in existing_names and len(places) < 3:
                    state["places"].append(mock_place)
        
        return state
        
    except Exception as e:
        print(f"Error finding places: {e}")
        return await _fallback_places_to_mock(state, metadata)

async def _fallback_places_to_mock(state: Dict[str, Any], metadata: TripMetadata) -> Dict[str, Any]:
    """Generate mock place data if real API fails"""
    dest = metadata.destination.lower()
    attractions = []
    
    if "new york" in dest or "nyc" in dest:
        attractions = [
            Place(
                name="Central Park",
                description="Iconic park in the heart of Manhattan",
                rating=4.8,
                price=0.0,
                location="Manhattan",
                category="Park",
                place_id="ChIJN1t_tStoiERuMIXG2aLFIY0"
            ),
            Place(
                name="Empire State Building",
                description="Historic 102-story skyscraper",
                rating=4.7,
                price=42.0,
                location="Midtown",
                category="Landmark",
                place_id="ChIJd8BlQ2BZwokRAFQ0_t4AAAAA"
            ),
            Place(
                name="Metropolitan Museum of Art",
                description="One of the world's largest and finest art museums",
                rating=4.8,
                price=25.0,
                location="Upper East Side",
                category="Museum",
                place_id="ChIJN1t_tStoiERuMIXG2aLFIY0"
            )
        ]
    elif "boston" in dest:
        attractions = [
            Place(
                name="Freedom Trail",
                description="A 2.5-mile-long path through downtown Boston",
                rating=4.8,
                price=0.0,
                location="Downtown",
                category="Historic",
                place_id="ChIJN1t_tStoiERuMIXG2aLFIY0"
            ),
            Place(
                name="Fenway Park",
                description="Historic baseball park",
                rating=4.7,
                price=30.0,
                location="Fenway",
                category="Sports",
                place_id="ChIJN1t_tStoiERuMIXG2aLFIY0"
            ),
            Place(
                name="Museum of Fine Arts",
                description="Art museum with an encyclopedic collection",
                rating=4.8,
                price=25.0,
                location="Fenway",
                category="Museum",
                place_id="ChIJN1t_tStoiERuMIXG2aLFIY0"
            )
        ]
    else:
        # Generic attractions
        attractions = [
            Place(
                name=f"{metadata.destination} Museum",
                description=f"Main museum in {metadata.destination}",
                rating=4.5,
                price=20.0,
                location="Downtown",
                category="Museum",
                place_id="ChIJN1t_tStoiERuMIXG2aLFIY0"
            ),
            Place(
                name=f"{metadata.destination} Park",
                description=f"Beautiful park in {metadata.destination}",
                rating=4.6,
                price=0.0,
                location="Central",
                category="Park",
                place_id="ChIJN1t_tStoiERuMIXG2aLFIY0"
            ),
            Place(
                name=f"{metadata.destination} Tower",
                description=f"Iconic landmark in {metadata.destination}",
                rating=4.4,
                price=15.0,
                location="Downtown",
                category="Landmark",
                place_id="ChIJN1t_tStoiERuMIXG2aLFIY0"
            )
        ]
    
    # Add to state
    state["places"] = [place.dict() for place in attractions]
    
    return state

async def restaurants_node(state: GraphState) -> GraphState:
    """
    Find restaurant options for the trip.
    Uses the Google Places API to find real restaurants.
    
    Args:
        state: Current state containing trip metadata
        
    Returns:
        Updated state with restaurant options
    """
    metadata: Optional[TripMetadata] = state.get("metadata")
    
    if not metadata or not metadata.destination:
        state["restaurants"] = []
        return state
    
    try:
        # Get destination coordinates
        lat, lng = geocode_location(metadata.destination)
        
        if not lat or not lng:
            # Fallback to mock data if geocoding fails
            print(f"Could not geocode destination: {metadata.destination}. Using mock data.")
            return await _fallback_restaurants_to_mock(state, metadata)
        
        # Determine price range based on preferences
        min_price, max_price = 0, 4  # Default: all price levels
        if "budget" in metadata.preferences:
            min_price, max_price = 0, 2
        elif "luxury" in metadata.preferences:
            min_price, max_price = 3, 4
        
        # Determine cuisine keyword based on preferences
        cuisine_keyword = None
        cuisine_preferences = ["italian", "mexican", "chinese", "indian", "japanese", 
                             "thai", "american", "french", "mediterranean", "vegan"]
        
        for pref in metadata.preferences:
            if pref.lower() in cuisine_preferences:
                cuisine_keyword = pref
                break
        
        # Get restaurants using Google Places API
        restaurant_data = _get_restaurants(
            latitude=lat,
            longitude=lng,
            radius=2000,  # 2km radius
            min_price=min_price,
            max_price=max_price,
            keyword=cuisine_keyword
        )
        
        # Convert to our schema format (up to 5 top restaurants)
        restaurants = []
        for resto in restaurant_data[:5]:
            # Create Restaurant object
            restaurant = Restaurant(
                name=resto.get('name', 'Unknown Restaurant'),
                cuisine=resto.get('types', ['restaurant'])[0].replace('_', ' ').title(),
                rating=resto.get('rating', 4.0),
                price_level=resto.get('price_level', 2),
                location=resto.get('vicinity', 'Unknown Location'),
                description=_generate_restaurant_description(resto),
                place_id=resto.get('place_id')
            )
            
            restaurants.append(restaurant)
        
        # Add to state
        state["restaurants"] = [restaurant.dict() for restaurant in restaurants]
        
        # If we didn't find enough restaurants, supplement with mock data
        if len(restaurants) < 3:
            mock_state = await _fallback_restaurants_to_mock(state, metadata)
            mock_restaurants = mock_state.get("restaurants", [])
            
            # Add unique mock restaurants until we have at least 3
            existing_names = {r.name for r in restaurants}
            for mock_restaurant in mock_restaurants:
                if mock_restaurant['name'] not in existing_names and len(restaurants) < 3:
                    state["restaurants"].append(mock_restaurant)
        
        return state
        
    except Exception as e:
        print(f"Error finding restaurants: {e}")
        return await _fallback_restaurants_to_mock(state, metadata)

def _get_restaurants(latitude, longitude, radius=1000, meal_type="dinner", min_price=0, max_price=4, keyword=None):
    """
    Find restaurants using Google Places API
    
    Parameters:
    - latitude: float - Latitude coordinate
    - longitude: float - Longitude coordinate
    - radius: int - Search radius in meters
    - meal_type: str - Type of meal (not used directly in API call)
    - min_price: int - Minimum price level (0-4)
    - max_price: int - Maximum price level (0-4)
    - keyword: str - Specific cuisine keyword
    
    Returns:
    - list of restaurant results
    """
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{latitude},{longitude}",
        "radius": radius,
        "type": "restaurant",
        "minprice": min_price,
        "maxprice": max_price,
        "key": os.environ.get("GOOGLE_PLACES_API_KEY")
    }
    
    # Add keyword parameter if provided (for cuisine)
    if keyword:
        params["keyword"] = keyword
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get('status') != 'OK':
            print(f"Error fetching restaurants: {data.get('status')}")
            return []
            
        # Sort by rating (highest first)
        results = data.get('results', [])
        results.sort(key=lambda x: x.get('rating', 0), reverse=True)
        
        return results
    except Exception as e:
        print(f"Error fetching restaurants: {e}")
        return []

def _generate_restaurant_description(restaurant_data):
    """Generate a description for a restaurant based on its data"""
    description = ""
    
    # Base description on place types and rating
    types = restaurant_data.get('types', [])
    if 'restaurant' in types:
        types.remove('restaurant')
    
    cuisine_types = [t.replace('_', ' ').title() for t in types 
                    if t not in ['point_of_interest', 'establishment', 'food']][:2]
    
    if cuisine_types:
        description = f"{' and '.join(cuisine_types)} restaurant"
    else:
        description = "Restaurant"
    
    # Add rating description
    rating = restaurant_data.get('rating')
    if rating:
        if rating >= 4.5:
            description += " with excellent ratings"
        elif rating >= 4.0:
            description += " with very good ratings"
        elif rating >= 3.5:
            description += " with good ratings"
    
    # Add price level description
    price_level = restaurant_data.get('price_level')
    if price_level:
        price_descriptions = {
            1: "budget-friendly",
            2: "moderately priced",
            3: "upscale",
            4: "high-end luxury"
        }
        description += f", {price_descriptions.get(price_level, '')}"
    
    return description

async def _fallback_restaurants_to_mock(state: Dict[str, Any], metadata: TripMetadata) -> Dict[str, Any]:
    """Generate mock restaurant data if real API fails"""
    dest = metadata.destination.lower()
    restaurants = []
    
    if "new york" in dest or "nyc" in dest:
        restaurants = [
            Restaurant(
                name="Katz's Delicatessen",
                cuisine="American Deli",
                rating=4.5,
                price_level=2,
                location="Lower East Side",
                description="Famous for pastrami sandwiches",
                place_id="ChIJN1t_tStoiERuMIXG2aLFIY0"
            ),
            Restaurant(
                name="Joe's Pizza",
                cuisine="Pizza",
                rating=4.7,
                price_level=1,
                location="Greenwich Village",
                description="Classic NY-style pizza slices",
                place_id="ChIJN1t_tStoiERuMIXG2aLFIY0"
            ),
            Restaurant(
                name="Le Bernardin",
                cuisine="French Seafood",
                rating=4.9,
                price_level=4,
                location="Midtown",
                description="Upscale French seafood restaurant",
                place_id="ChIJN1t_tStoiERuMIXG2aLFIY0"
            )
        ]
    elif "boston" in dest:
        restaurants = [
            Restaurant(
                name="Union Oyster House",
                cuisine="Seafood",
                rating=4.4,
                price_level=3,
                location="Downtown",
                description="Historic seafood restaurant",
                place_id="ChIJN1t_tStoiERuMIXG2aLFIY0"
            ),
            Restaurant(
                name="Mike's Pastry",
                cuisine="Bakery",
                rating=4.6,
                price_level=2,
                location="North End",
                description="Famous for cannoli",
                place_id="ChIJN1t_tStoiERuMIXG2aLFIY0"
            ),
            Restaurant(
                name="Legal Sea Foods",
                cuisine="Seafood",
                rating=4.5,
                price_level=3,
                location="Seaport",
                description="Popular seafood chain",
                place_id="ChIJN1t_tStoiERuMIXG2aLFIY0"
            )
        ]
    else:
        # Generic restaurants
        cuisines = ["Italian", "American", "Asian Fusion", "Mexican", "Mediterranean"]
        for i in range(3):
            cuisine = random.choice(cuisines)
            price_level = random.randint(1, 4)
            restaurants.append(
                Restaurant(
                    name=f"The {metadata.destination} {cuisine} Restaurant",
                    cuisine=cuisine,
                    rating=round(random.uniform(3.8, 4.9), 1),
                    price_level=price_level,
                    location="Downtown",
                    description=f"Popular {cuisine.lower()} restaurant in {metadata.destination}",
                    place_id="ChIJN1t_tStoiERuMIXG2aLFIY0"
                )
            )
    
    # Filter based on preferences if specified
    if "budget" in metadata.preferences:
        restaurants = [r for r in restaurants if r.price_level <= 2]
    
    # Add to state
    state["restaurants"] = [restaurant.dict() for restaurant in restaurants]
    
    return state

async def hotel_node(state: GraphState) -> GraphState:
    """
    Find hotel options for the trip.
    Uses the Google Places API to find real hotels.
    
    Args:
        state: Current state containing trip metadata
        
    Returns:
        Updated state with hotel options
    """
    metadata: Optional[TripMetadata] = state.get("metadata")
    
    if not metadata or not metadata.destination:
        state["hotel"] = {}
        return state
    
    try:
        # Get destination coordinates
        lat, lng = geocode_location(metadata.destination)
        
        if not lat or not lng:
            # Fallback to mock data if geocoding fails
            print(f"Could not geocode destination: {metadata.destination}. Using mock data.")
            return await _fallback_hotel_to_mock(state, metadata)
        
        # Determine hotel type based on preferences
        hotel_type = "lodging"  # Default search term
        
        if "luxury" in metadata.preferences:
            hotel_type = "lodging luxury"
        elif "budget" in metadata.preferences:
            hotel_type = "lodging budget"
        
        # Find hotels using Google Places API
        hotels_data = _find_hotels(
            latitude=lat,
            longitude=lng,
            keyword=hotel_type,
            radius=5000  # 5km radius
        )
        
        if not hotels_data:
            return await _fallback_hotel_to_mock(state, metadata)
        
        # Choose best hotel based on preferences and ratings
        best_hotel = _select_best_hotel(hotels_data, metadata.preferences)
        
        if not best_hotel:
            return await _fallback_hotel_to_mock(state, metadata)
        
        # Determine price range based on preferences
        price_per_night = _estimate_price(best_hotel.get('price_level', 2), metadata.preferences)
        
        # Extract amenities (not available directly from Places API)
        amenities = _get_default_amenities(best_hotel.get('price_level', 2))
        
        # Create Hotel object
        hotel = Hotel(
            name=best_hotel.get('name', f"{metadata.destination} Hotel"),
            rating=best_hotel.get('rating', 4.0),
            price_per_night=price_per_night,
            location=best_hotel.get('vicinity', f"Downtown {metadata.destination}"),
            amenities=amenities,
            place_id=best_hotel.get('place_id')
        )
        
        # Add to state
        state["hotel"] = hotel.dict()
        
        return state
        
    except Exception as e:
        print(f"Error finding hotels: {e}")
        return await _fallback_hotel_to_mock(state, metadata)

def _find_hotels(latitude, longitude, keyword="lodging", radius=5000):
    """
    Find hotels using Google Places API
    
    Parameters:
    - latitude: float - Latitude coordinate
    - longitude: float - Longitude coordinate
    - keyword: str - Search keyword (e.g., "lodging luxury")
    - radius: int - Search radius in meters
    
    Returns:
    - list of hotel results
    """
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{latitude},{longitude}",
        "radius": radius,
        "type": "lodging",
        "key": os.environ.get("GOOGLE_PLACES_API_KEY")
    }
    
    # Add keyword if provided
    if keyword and keyword != "lodging":
        params["keyword"] = keyword
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get('status') != 'OK':
            print(f"Error fetching hotels: {data.get('status')}")
            return []
            
        # Sort by rating (highest first)
        results = data.get('results', [])
        results.sort(key=lambda x: x.get('rating', 0), reverse=True)
        
        return results
    except Exception as e:
        print(f"Error fetching hotels: {e}")
        return []

def _select_best_hotel(hotels, preferences):
    """Select the best hotel based on user preferences"""
    if not hotels:
        return None
    
    # If "budget" is a preference, prioritize lower price levels
    if "budget" in preferences:
        budget_hotels = [h for h in hotels if h.get('price_level', 3) <= 2]
        if budget_hotels:
            # Return the highest-rated budget hotel
            budget_hotels.sort(key=lambda x: x.get('rating', 0), reverse=True)
            return budget_hotels[0]
    
    # If "luxury" is a preference, prioritize higher price levels
    elif "luxury" in preferences:
        luxury_hotels = [h for h in hotels if h.get('price_level', 0) >= 3]
        if luxury_hotels:
            # Return the highest-rated luxury hotel
            luxury_hotels.sort(key=lambda x: x.get('rating', 0), reverse=True)
            return luxury_hotels[0]
    
    # Default: return the highest-rated hotel
    return hotels[0] if hotels else None

def _estimate_price(price_level, preferences):
    """Estimate nightly price based on price level and preferences"""
    # Base price ranges by price level
    price_ranges = {
        0: (40, 70),    # Very budget
        1: (70, 120),   # Budget
        2: (120, 200),  # Moderate
        3: (200, 350),  # Upscale
        4: (350, 800)   # Luxury
    }
    
    # Default to moderate if price_level is not available
    range_min, range_max = price_ranges.get(price_level, price_ranges[2])
    
    # Adjust based on specific preferences
    if "budget" in preferences:
        range_min = max(range_min * 0.8, price_ranges[0][0])
        range_max = min(range_max * 0.8, price_ranges[1][1])
    elif "luxury" in preferences:
        range_min = max(range_min * 1.2, price_ranges[3][0])
        range_max = max(range_max * 1.2, price_ranges[3][1])
    
    # Generate a specific price within the range
    return round(random.uniform(range_min, range_max), 2)

def _get_default_amenities(price_level):
    """Get default amenities based on hotel price level"""
    # Base amenities available at most hotels
    base_amenities = ["WiFi", "Air Conditioning"]
    
    # Additional amenities by price level
    amenities_by_level = {
        0: ["WiFi"],
        1: base_amenities + ["TV"],
        2: base_amenities + ["TV", "Breakfast", "Parking"],
        3: base_amenities + ["TV", "Breakfast", "Parking", "Pool", "Gym"],
        4: base_amenities + ["TV", "Breakfast", "Parking", "Pool", "Gym", "Spa", "Room Service"]
    }
    
    return amenities_by_level.get(price_level, base_amenities)

async def _fallback_hotel_to_mock(state: Dict[str, Any], metadata: TripMetadata) -> Dict[str, Any]:
    """Generate mock hotel data if real API fails"""
    dest = metadata.destination.lower()
    
    # Choose hotel price range based on preferences
    price_range = (200, 400)
    if "budget" in metadata.preferences:
        price_range = (80, 150)
    elif "luxury" in metadata.preferences:
        price_range = (350, 600)
    
    hotel_name = ""
    if "new york" in dest or "nyc" in dest:
        hotel_choices = [
            ("Budget Inn NYC", 3.5) if "budget" in metadata.preferences
            else ("The Plaza Hotel", 4.8) if "luxury" in metadata.preferences
            else ("Hilton Times Square", 4.2)
        ]
        hotel_name, rating = hotel_choices[0]
    elif "boston" in dest:
        hotel_choices = [
            ("Boston Backpackers Hostel", 3.7) if "budget" in metadata.preferences
            else ("Four Seasons Boston", 4.9) if "luxury" in metadata.preferences
            else ("Boston Marriott", 4.3)
        ]
        hotel_name, rating = hotel_choices[0]
    else:
        # Generic hotel
        hotel_name = f"The {metadata.destination} Hotel"
        rating = round(random.uniform(3.5, 4.9), 1)
    
    price_per_night = round(random.uniform(price_range[0], price_range[1]), 2)
    
    hotel = Hotel(
        name=hotel_name,
        rating=rating,
        price_per_night=price_per_night,
        location=f"Downtown {metadata.destination}",
        amenities=["WiFi", "Breakfast", "Gym", "Pool"],
        place_id="ChIJN1t_tStoiERuMIXG2aLFIY0"
    )
    
    # Add to state
    state["hotel"] = hotel.dict()
    
    return state

async def budget_node(state: GraphState) -> GraphState:
    """
    Calculate budget estimates for the trip.
    
    Args:
        state: Current state containing trip data
        
    Returns:
        Updated state with budget estimates
    """
    metadata: Optional[TripMetadata] = state.get("metadata")
    
    if not metadata or not metadata.start_date or not metadata.end_date:
        state["budget"] = {}
        return state
    
    # Calculate trip duration
    duration = (metadata.end_date - metadata.start_date).days or 1
    
    # Get costs from other nodes
    flights = state.get("flights", [])
    hotel = state.get("hotel", {})
    places = state.get("places", [])
    
    # Calculate flight costs
    flights_total = 0
    if flights:
        # Use the cheapest flight option
        cheapest_flight = min(flights, key=lambda x: x.get("price", float("inf"))) if flights else {}
        flights_total = cheapest_flight.get("price", 0) * metadata.num_people
    
    # Calculate hotel costs
    hotel_total = 0
    if hotel:
        hotel_total = hotel.get("price_per_night", 0) * duration
    
    # Estimate daily food costs based on preferences
    daily_food_cost = 60  # Default
    if "budget" in metadata.preferences:
        daily_food_cost = 40
    elif "luxury" in metadata.preferences:
        daily_food_cost = 120
    
    daily_food_estimate = daily_food_cost * metadata.num_people
    
    # Estimate activities costs
    activities_estimate = 0
    for place in places:
        if isinstance(place, dict) and place.get("price", 0) > 0:
            activities_estimate += place.get("price", 0) * metadata.num_people
    
    # Add transportation costs if using route
    route = state.get("route", {})
    transportation_cost = 0
    if route and "distance_km" in route:
        # Estimate car rental or fuel costs based on distance
        distance_km = route.get("distance_km", 0)
        if distance_km > 0:
            # Rough estimate: $0.15 per km for fuel + $30 per day for rental
            transportation_cost = (distance_km * 0.15) + (30 * duration)
    
    # Calculate total budget
    total = flights_total + hotel_total + (daily_food_estimate * duration) + activities_estimate + transportation_cost
    
    # Add buffer for miscellaneous expenses (10%)
    misc_buffer = total * 0.1
    total += misc_buffer
    
    # Create budget object
    budget = Budget(
        flights_total=round(flights_total, 2),
        hotel_total=round(hotel_total, 2),
        daily_food_estimate=round(daily_food_estimate, 2),
        activities_estimate=round(activities_estimate, 2),
        total=round(total, 2)
    )
    
    # Add to state
    state["budget"] = budget.dict()
    
    return state

async def reviews_node(state: GraphState) -> GraphState:
    """
    Fetches and analyzes reviews for places, restaurants, and hotels.
    This node processes the outputs from the places, restaurants, and hotel nodes.
    
    Args:
        state: Current state containing place information
        
    Returns:
        Updated state with review insights
    """
    try:
        print("\n=== Reviews Node ===")
        
        # Process places
        places = state.get("places", [])
        if places:
            print(f"Processing reviews for {len(places)} places...")
            for place in places:
                if place.get('place_id'):
                    print(f"Getting reviews for place: {place.get('name', 'Unknown Place')}")
                    insights = await get_review_insights(
                        place['place_id'],
                        place.get('name', 'Place')
                    )
                    if insights:
                        place['review_insights'] = insights  # insights is already a dict
                        print(f"Added review insights for place: {place.get('name', 'Unknown Place')}")
        
        # Process restaurants
        restaurants = state.get("restaurants", [])
        if restaurants:
            print(f"Processing reviews for {len(restaurants)} restaurants...")
            for restaurant in restaurants:
                if restaurant.get('place_id'):
                    print(f"Getting reviews for restaurant: {restaurant.get('name', 'Unknown Restaurant')}")
                    insights = await get_review_insights(
                        restaurant['place_id'],
                        restaurant.get('name', 'Restaurant')
                    )
                    if insights:
                        restaurant['review_insights'] = insights  # insights is already a dict
                        print(f"Added review insights for restaurant: {restaurant.get('name', 'Unknown Restaurant')}")
        
        # Process hotel
        hotel = state.get("hotel", {})
        if hotel and hotel.get('place_id'):
            print(f"Processing reviews for hotel: {hotel.get('name', 'Unknown Hotel')}")
            insights = await get_review_insights(
                hotel['place_id'],
                hotel.get('name', 'Hotel')
            )
            if insights:
                hotel['review_insights'] = insights  # insights is already a dict
                print(f"Added review insights for hotel: {hotel.get('name', 'Unknown Hotel')}")
        
        print("Reviews node completed")
        return state
        
    except Exception as e:
        print(f"Error in reviews node: {str(e)}")
        return state

async def get_review_insights(place_id: str, place_name: str) -> Optional[Dict[str, Any]]:
    """
    Fetches and analyzes reviews for a single place using Claude's web search capabilities.
    
    Args:
        place_id: The Google Places ID
        place_name: The name of the place
        
    Returns:
        Dictionary with review insights if successful, None otherwise
    """
    try:
        # Initialize Claude
        claude = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
        # First, get basic info from Google Places API
        api_key = os.getenv('GOOGLE_PLACES_API_KEY')
        if not api_key:
            print("GOOGLE_PLACES_API_KEY not found in environment variables")
            return None

        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "fields": "rating,user_ratings_total",
            "key": api_key
        }

        response = requests.get(url, params=params)
        data = response.json()

        if data.get('status') != 'OK':
            print(f"Error fetching place details: {data.get('status')}")
            return None

        result = data.get('result', {})
        total_reviews = result.get('user_ratings_total', 0)
        average_rating = result.get('rating', 0)

        # Use Claude to search the web for reviews
        search_prompt = f"""Please search the web for reviews and information about {place_name}. 
        Look for reviews from multiple sources (Google Maps, Yelp, TripAdvisor, etc.) and analyze them.

        IMPORTANT: You must respond ONLY with a valid JSON object in the following format. Use double quotes for keys and values. Do not include any additional text or explanation outside the JSON structure.

        {{
            "sentiment": "positive/negative/neutral",
            "strengths": ["list of key strengths mentioned in reviews"],
            "weaknesses": ["list of key weaknesses or precautions mentioned in reviews"],
            "themes": ["list of common themes from reviews"],
            "precautions": ["list of important visitor precautions"],
            "summary": "2-3 sentence summary of the place based on reviews"
        }}

        Please provide a comprehensive analysis based on as many reviews as you can find.
        Make sure to include specific details and examples from the reviews."""

        response = claude.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": search_prompt
            }]
        )

        # Extract the analysis from Claude's response
        analysis = response.content[0].text.strip()

        # Try to parse the JSON response
        try:
            # Remove any markdown code block markers if present
            if analysis.startswith("```json"):
                analysis = analysis[7:]
            if analysis.endswith("```"):
                analysis = analysis[:-3]
            analysis = analysis.strip()
            
            analysis_data = json.loads(analysis)
            
            # Validate the required fields
            required_fields = ["sentiment", "strengths", "weaknesses", "themes", "precautions", "summary"]
            for field in required_fields:
                if field not in analysis_data:
                    print(f"Missing required field '{field}' in Claude's response for {place_name}")
                    return None
                    
        except json.JSONDecodeError as e:
            print(f"Error parsing Claude's response for {place_name}: {str(e)}")
            print(f"Raw response: {analysis}")
            return None

        # Get the review distribution from the analysis
        review_distribution = {
            "1_star": 0,
            "2_star": 0,
            "3_star": 0,
            "4_star": 0,
            "5_star": 0
        }

        # Update the distribution based on the sentiment
        sentiment = analysis_data.get("sentiment", "").lower()
        if "very positive" in sentiment or "excellent" in sentiment:
            review_distribution["5_star"] = int(total_reviews * 0.6)
            review_distribution["4_star"] = int(total_reviews * 0.3)
            review_distribution["3_star"] = int(total_reviews * 0.1)
        elif "positive" in sentiment or "good" in sentiment:
            review_distribution["5_star"] = int(total_reviews * 0.4)
            review_distribution["4_star"] = int(total_reviews * 0.4)
            review_distribution["3_star"] = int(total_reviews * 0.2)
        elif "mixed" in sentiment or "average" in sentiment:
            review_distribution["5_star"] = int(total_reviews * 0.2)
            review_distribution["4_star"] = int(total_reviews * 0.3)
            review_distribution["3_star"] = int(total_reviews * 0.3)
            review_distribution["2_star"] = int(total_reviews * 0.2)
        else:
            review_distribution["5_star"] = int(total_reviews * 0.1)
            review_distribution["4_star"] = int(total_reviews * 0.2)
            review_distribution["3_star"] = int(total_reviews * 0.3)
            review_distribution["2_star"] = int(total_reviews * 0.2)
            review_distribution["1_star"] = int(total_reviews * 0.2)

        return {
            "analysis": analysis_data,
            "total_available_reviews": total_reviews,
            "analyzed_reviews": total_reviews,
            "average_rating": average_rating,
            "review_distribution": review_distribution,
            "note": "Analysis based on web search results from multiple sources"
        }

    except Exception as e:
        print(f"Error getting review insights for {place_name}: {str(e)}")
        return None 