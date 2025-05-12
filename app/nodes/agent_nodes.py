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

# Helper functions for mock data generation
async def _generate_mock_flights(state: Dict[str, Any]) -> Dict[str, Any]:
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