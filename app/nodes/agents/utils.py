import os
import requests
import googlemaps
import random
from app.schemas.trip_schema import Hotel, TripMetadata
from datetime import datetime, timedelta

# Geocode a location name to latitude and longitude
def geocode_location(location_name, gmaps=None):
    """Convert a location name to latitude and longitude coordinates"""
    if hasattr(geocode_location, 'cache') and location_name in geocode_location.cache:
        return geocode_location.cache[location_name]
    if not hasattr(geocode_location, 'cache'):
        geocode_location.cache = {}
    if gmaps is None:
        api_key = os.environ.get("GOOGLE_PLACES_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_PLACES_API_KEY environment variable not set")
        gmaps = googlemaps.Client(key=api_key)
    try:
        geocode_result = gmaps.geocode(location_name)
        if geocode_result and len(geocode_result) > 0:
            location = geocode_result[0]['geometry']['location']
            result = (location['lat'], location['lng'])
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
    """
    if radius > 50000:
        print(f"Warning: Radius reduced from {radius}m to 50000m (API maximum)")
        radius = 50000
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    base_params = {
        "location": f"{city_lat},{city_lng}",
        "radius": radius,
        "key": os.environ.get("GOOGLE_PLACES_API_KEY")
    }
    results = []
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
        for place_type in place_types:
            type_params = base_params.copy()
            type_params["type"] = place_type
            response = requests.get(url, params=type_params)
            result_data = response.json()
            if result_data.get('status') == "OK" and result_data.get('results'):
                print(f"Found {len(result_data.get('results'))} results for '{place_type}'")
                results.extend(result_data.get('results'))
    unique_results = {}
    for item in results:
        if 'place_id' in item:
            unique_results[item['place_id']] = item
    results = list(unique_results.values())
    if sort_by == "rating":
        results.sort(key=lambda x: (x.get('rating', 0) or 0, x.get('user_ratings_total', 0) or 0), reverse=True)
    elif sort_by == "reviews":
        results.sort(key=lambda x: x.get('user_ratings_total', 0) or 0, reverse=True)
    print(f"Total unique attractions found in {city_name}: {len(results)}")
    return results

# Get restaurants in a city
def _get_restaurants(latitude, longitude, radius=1000, meal_type="dinner", min_price=0, max_price=4, keyword=None):
    """
    Find restaurants using Google Places API
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
    if keyword:
        params["keyword"] = keyword
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data.get('status') != 'OK':
            print(f"Error fetching restaurants: {data.get('status')}")
            return []
        results = data.get('results', [])
        results.sort(key=lambda x: x.get('rating', 0), reverse=True)
        return results
    except Exception as e:
        print(f"Error fetching restaurants: {e}")
        return []

def get_gmaps_client():
    """Get a Google Maps client instance with API key from environment."""
    api_key = os.environ.get("GOOGLE_PLACES_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_PLACES_API_KEY environment variable not set")
    return googlemaps.Client(key=api_key)

def _find_hotels(latitude, longitude, keyword="lodging", radius=5000):
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{latitude},{longitude}",
        "radius": radius,
        "type": "lodging",
        "key": os.environ.get("GOOGLE_PLACES_API_KEY")
    }
    if keyword and keyword != "lodging":
        params["keyword"] = keyword
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data.get('status') != 'OK':
            print(f"Error fetching hotels: {data.get('status')}")
            return []
        results = data.get('results', [])
        results.sort(key=lambda x: x.get('rating', 0), reverse=True)
        return results
    except Exception as e:
        print(f"Error fetching hotels: {e}")
        return []

def _select_best_hotel(hotels, preferences):
    if not hotels:
        return None
    if "budget" in preferences:
        budget_hotels = [h for h in hotels if h.get('price_level', 3) <= 2]
        if budget_hotels:
            budget_hotels.sort(key=lambda x: x.get('rating', 0), reverse=True)
            return budget_hotels[0]
    elif "luxury" in preferences:
        luxury_hotels = [h for h in hotels if h.get('price_level', 0) >= 3]
        if luxury_hotels:
            luxury_hotels.sort(key=lambda x: x.get('rating', 0), reverse=True)
            return luxury_hotels[0]
    return hotels[0] if hotels else None

def _get_default_amenities(price_level):
    base_amenities = ["WiFi", "Air Conditioning"]
    amenities_by_level = {
        0: ["WiFi"],
        1: base_amenities + ["TV"],
        2: base_amenities + ["TV", "Breakfast", "Parking"],
        3: base_amenities + ["TV", "Breakfast", "Parking", "Pool", "Gym"],
        4: base_amenities + ["TV", "Breakfast", "Parking", "Pool", "Gym", "Spa", "Room Service"]
    }
    return amenities_by_level.get(price_level, base_amenities)

def _estimate_price(price_level, preferences):
    price_ranges = {
        0: (40, 70),
        1: (70, 120),
        2: (120, 200),
        3: (200, 350),
        4: (350, 800)
    }
    range_min, range_max = price_ranges.get(price_level, price_ranges[2])
    if "budget" in preferences:
        range_min = max(range_min * 0.8, price_ranges[0][0])
        range_max = min(range_max * 0.8, price_ranges[1][1])
    elif "luxury" in preferences:
        range_min = max(range_min * 1.2, price_ranges[3][0])
        range_max = max(range_max * 1.2, price_ranges[3][1])
    return round(random.uniform(range_min, range_max), 2)

async def _fallback_hotel_to_mock(state: dict, metadata: dict) -> dict:
    dest = metadata.get('destination', '').lower()
    price_range = (200, 400)
    preferences = metadata.get('preferences', [])
    if "budget" in preferences:
        price_range = (80, 150)
    elif "luxury" in preferences:
        price_range = (350, 600)
    hotel_name = ""
    if "new york" in dest or "nyc" in dest:
        hotel_choices = [
            ("Budget Inn NYC", 3.5) if "budget" in preferences
            else ("The Plaza Hotel", 4.8) if "luxury" in preferences
            else ("Hilton Times Square", 4.2)
        ]
        hotel_name, rating = hotel_choices[0]
    elif "boston" in dest:
        hotel_choices = [
            ("Boston Backpackers Hostel", 3.7) if "budget" in preferences
            else ("Four Seasons Boston", 4.9) if "luxury" in preferences
            else ("Boston Marriott", 4.3)
        ]
        hotel_name, rating = hotel_choices[0]
    else:
        hotel_name = f"The {metadata.get('destination', 'City')} Hotel"
        rating = round(random.uniform(3.5, 4.9), 1)
    price_per_night = round(random.uniform(price_range[0], price_range[1]), 2)
    hotel = Hotel(
        name=hotel_name,
        rating=rating,
        price_per_night=price_per_night,
        location=f"Downtown {metadata.get('destination', '')}",
        amenities=["WiFi", "Breakfast", "Gym", "Pool"],
        place_id="ChIJN1t_tStoiERuMIXG2aLFIY0"
    )
    state["hotel"] = hotel.dict()
    return state 