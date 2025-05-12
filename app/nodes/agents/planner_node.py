from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import os
import requests
import googlemaps
from anthropic import Anthropic
import json

from app.schemas.trip_schema import TripMetadata
from app.nodes.agents.common import geocode_location, get_places

async def get_place_with_reviews(place: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get a place with its reviews and additional information for itinerary planning.
    
    Args:
        place: Place information from places_node
        
    Returns:
        Enhanced place information with reviews and timing estimates
    """
    try:
        # Get reviews for the place
        insights = await get_review_insights(
            place['place_id'],
            place.get('name', 'Place')
        )
        
        # Estimate visit duration based on category and reviews
        duration = estimate_visit_duration(place.get('category', ''), insights)
        
        # Get opening hours (if available)
        opening_hours = get_opening_hours(place.get('place_id'))
        
        # Enhanced place information
        enhanced_place = {
            **place,
            "reviews": insights,
            "estimated_duration": duration,
            "opening_hours": opening_hours,
            "best_time_to_visit": get_best_time_to_visit(insights, opening_hours),
            "travel_time_from_hotel": None,  # To be filled by route optimization
            "travel_time_to_next": None,     # To be filled by route optimization
        }
        
        return enhanced_place
        
    except Exception as e:
        print(f"Error enhancing place with reviews: {e}")
        return place

def estimate_visit_duration(category: str, reviews: Optional[Dict[str, Any]]) -> int:
    """
    Estimate how long a visit to a place might take based on its category and reviews.
    
    Args:
        category: Place category
        reviews: Review insights
        
    Returns:
        Estimated duration in minutes
    """
    # Base durations by category
    base_durations = {
        "Museum": 120,
        "Park": 90,
        "Landmark": 60,
        "Restaurant": 90,
        "Shopping": 60,
        "Entertainment": 120,
        "Historic Site": 90,
        "Art Gallery": 60,
        "Zoo": 180,
        "Aquarium": 120
    }
    
    # Get base duration
    duration = base_durations.get(category, 60)
    
    # Adjust based on reviews if available
    if reviews and "analysis" in reviews:
        analysis = reviews["analysis"]
        
        # Adjust for complexity
        if "complex" in analysis.get("themes", []):
            duration *= 1.2
        if "simple" in analysis.get("themes", []):
            duration *= 0.8
            
        # Adjust for popularity
        if "crowded" in analysis.get("precautions", []):
            duration *= 1.1
            
        # Adjust for size
        if "large" in analysis.get("themes", []):
            duration *= 1.3
        if "small" in analysis.get("themes", []):
            duration *= 0.7
    
    return int(duration)

def get_opening_hours(place_id: str) -> Dict[str, Any]:
    """
    Get opening hours for a place using Google Places API.
    
    Args:
        place_id: Google Places ID
        
    Returns:
        Dictionary with opening hours information
    """
    try:
        api_key = os.getenv('GOOGLE_PLACES_API_KEY')
        if not api_key:
            return {}
            
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "fields": "opening_hours",
            "key": api_key
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get('status') == 'OK' and 'result' in data:
            return data['result'].get('opening_hours', {})
            
        return {}
        
    except Exception as e:
        print(f"Error getting opening hours: {e}")
        return {}

def get_best_time_to_visit(reviews: Optional[Dict[str, Any]], opening_hours: Dict[str, Any]) -> str:
    """
    Determine the best time to visit based on reviews and opening hours.
    
    Args:
        reviews: Review insights
        opening_hours: Opening hours information
        
    Returns:
        Recommended time to visit
    """
    if not reviews or "analysis" not in reviews:
        return "Anytime during opening hours"
        
    analysis = reviews["analysis"]
    themes = analysis.get("themes", [])
    precautions = analysis.get("precautions", [])
    
    # Check for specific timing recommendations
    if "morning" in themes or "early" in themes:
        return "Morning (9 AM - 11 AM)"
    elif "evening" in themes or "sunset" in themes:
        return "Evening (4 PM - 6 PM)"
    elif "crowded" in precautions:
        return "Early morning or late afternoon"
    elif "quiet" in themes:
        return "Midday (12 PM - 2 PM)"
        
    return "Anytime during opening hours"

async def plan_daily_itinerary(
    places: List[Dict[str, Any]],
    hotel_location: Dict[str, float],
    date: datetime,
    preferences: List[str]
) -> Dict[str, Any]:
    """
    Plan a daily itinerary using enhanced place information.
    
    Args:
        places: List of enhanced places with reviews
        hotel_location: Hotel coordinates (lat, lng)
        date: Date for the itinerary
        preferences: User preferences
        
    Returns:
        Daily itinerary with optimized route
    """
    try:
        # Filter places based on opening hours and preferences
        available_places = []
        for place in places:
            opening_hours = place.get('opening_hours', {})
            if not opening_hours.get('open_now', True):
                continue
                
            # Check if place matches preferences
            if preferences:
                place_themes = place.get('reviews', {}).get('analysis', {}).get('themes', [])
                if not any(pref.lower() in ' '.join(place_themes).lower() for pref in preferences):
                    continue
                    
            available_places.append(place)
        
        # Sort places by rating and reviews
        available_places.sort(
            key=lambda x: (
                x.get('rating', 0),
                x.get('reviews', {}).get('average_rating', 0),
                x.get('reviews', {}).get('total_available_reviews', 0)
            ),
            reverse=True
        )
        
        # Calculate total available time (assuming 8 hours of activities)
        total_available_time = 8 * 60  # 8 hours in minutes
        current_time = 0
        selected_places = []
        
        # Select places that fit within the time constraint
        for place in available_places:
            duration = place.get('estimated_duration', 60)
            if current_time + duration <= total_available_time:
                selected_places.append(place)
                current_time += duration
            if current_time >= total_available_time:
                break
        
        # Optimize route between selected places
        optimized_route = optimize_route(selected_places, hotel_location)
        
        # Create daily itinerary
        daily_itinerary = {
            "date": date.strftime("%Y-%m-%d"),
            "places": optimized_route,
            "total_duration": current_time,
            "estimated_cost": sum(place.get('price', 0) for place in selected_places),
            "summary": generate_daily_summary(selected_places, optimized_route)
        }
        
        return daily_itinerary
        
    except Exception as e:
        print(f"Error planning daily itinerary: {e}")
        return {}

def optimize_route(places: List[Dict[str, Any]], hotel_location: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Optimize the route between places using Google Maps Distance Matrix API.
    
    Args:
        places: List of places to visit
        hotel_location: Hotel coordinates
        
    Returns:
        List of places in optimized order with travel times
    """
    try:
        api_key = os.getenv('GOOGLE_PLACES_API_KEY')
        if not api_key:
            return places
            
        # Get coordinates for all places
        coordinates = []
        for place in places:
            lat, lng = geocode_location(place.get('location', ''))
            if lat and lng:
                coordinates.append((lat, lng))
            else:
                coordinates.append((None, None))
        
        # Calculate distances using Google Maps API
        gmaps = googlemaps.Client(key=api_key)
        
        # Start from hotel
        current_location = hotel_location
        optimized_places = []
        remaining_places = list(zip(places, coordinates))
        
        while remaining_places:
            # Find nearest place
            min_distance = float('inf')
            nearest_idx = 0
            
            for i, (place, coords) in enumerate(remaining_places):
                if coords[0] is None or coords[1] is None:
                    continue
                    
                # Get distance from current location
                result = gmaps.distance_matrix(
                    current_location,
                    coords,
                    mode="driving"
                )
                
                if result['status'] == 'OK':
                    distance = result['rows'][0]['elements'][0]['distance']['value']
                    if distance < min_distance:
                        min_distance = distance
                        nearest_idx = i
            
            # Add nearest place to route
            place, coords = remaining_places.pop(nearest_idx)
            if coords[0] is not None and coords[1] is not None:
                current_location = coords
                
                # Add travel time to place
                place['travel_time_from_hotel'] = min_distance / 1000  # Convert to km
                optimized_places.append(place)
        
        return optimized_places
        
    except Exception as e:
        print(f"Error optimizing route: {e}")
        return places

def generate_daily_summary(places: List[Dict[str, Any]], route: List[Dict[str, Any]]) -> str:
    """
    Generate a summary of the daily itinerary.
    
    Args:
        places: List of places to visit
        route: Optimized route between places
        
    Returns:
        Summary of the day's activities
    """
    if not places:
        return "No activities planned for this day."
        
    summary = f"Today's itinerary includes {len(places)} attractions:\n\n"
    
    for i, place in enumerate(places, 1):
        # Get review insights
        insights = place.get('reviews', {}).get('analysis', {})
        best_time = place.get('best_time_to_visit', 'Anytime during opening hours')
        
        summary += f"{i}. {place['name']}\n"
        summary += f"   - Best time to visit: {best_time}\n"
        summary += f"   - Estimated duration: {place.get('estimated_duration', 60)} minutes\n"
        
        if insights:
            summary += f"   - Highlights: {', '.join(insights.get('strengths', [])[:2])}\n"
            
        if i < len(places):
            summary += f"   - Travel time to next: {place.get('travel_time_to_next', 0):.1f} km\n\n"
    
    return summary

async def generate_complete_itinerary(
    trip_metadata: Dict[str, Any],
    preferences: List[str]
) -> Dict[str, Any]:
    """
    Generate a complete itinerary for the entire trip.
    
    Args:
        trip_metadata: Trip metadata including dates, location, etc.
        preferences: User preferences
        
    Returns:
        Complete itinerary with daily plans
    """
    try:
        # Get hotel location
        hotel_location = geocode_location(trip_metadata.get('hotel', {}).get('address', ''))
        if not hotel_location:
            raise ValueError("Could not geocode hotel location")
            
        # Get all available places
        places = await get_places(
            trip_metadata.get('location', ''),
            trip_metadata.get('preferences', [])
        )
        
        # Enhance places with reviews
        enhanced_places = []
        for place in places:
            enhanced_place = await get_place_with_reviews(place)
            enhanced_places.append(enhanced_place)
        
        # Generate daily itineraries
        daily_itineraries = []
        current_date = trip_metadata.get('start_date')
        end_date = trip_metadata.get('end_date')
        
        while current_date <= end_date:
            daily_itinerary = await plan_daily_itinerary(
                enhanced_places,
                hotel_location,
                current_date,
                preferences
            )
            
            if daily_itinerary:
                daily_itineraries.append(daily_itinerary)
                
            current_date += timedelta(days=1)
        
        # Generate complete itinerary
        complete_itinerary = {
            "trip_summary": {
                "destination": trip_metadata.get('location', ''),
                "start_date": trip_metadata.get('start_date').strftime("%Y-%m-%d"),
                "end_date": trip_metadata.get('end_date').strftime("%Y-%m-%d"),
                "total_days": len(daily_itineraries),
                "preferences": preferences,
                "estimated_total_cost": sum(day.get('estimated_cost', 0) for day in daily_itineraries)
            },
            "daily_itineraries": daily_itineraries,
            "recommendations": generate_trip_recommendations(daily_itineraries, preferences)
        }
        
        return complete_itinerary
        
    except Exception as e:
        print(f"Error generating complete itinerary: {e}")
        return {}

def generate_trip_recommendations(
    daily_itineraries: List[Dict[str, Any]],
    preferences: List[str]
) -> Dict[str, Any]:
    """
    Generate recommendations for the entire trip.
    
    Args:
        daily_itineraries: List of daily itineraries
        preferences: User preferences
        
    Returns:
        Dictionary of recommendations
    """
    try:
        # Collect all places
        all_places = []
        for day in daily_itineraries:
            all_places.extend(day.get('places', []))
        
        # Analyze themes and preferences
        themes = {}
        for place in all_places:
            place_themes = place.get('reviews', {}).get('analysis', {}).get('themes', [])
            for theme in place_themes:
                themes[theme] = themes.get(theme, 0) + 1
        
        # Generate recommendations
        recommendations = {
            "packing_suggestions": generate_packing_suggestions(themes, preferences),
            "local_tips": generate_local_tips(all_places),
            "safety_precautions": collect_safety_precautions(all_places),
            "budget_tips": generate_budget_tips(all_places),
            "alternative_activities": suggest_alternatives(all_places, preferences)
        }
        
        return recommendations
        
    except Exception as e:
        print(f"Error generating trip recommendations: {e}")
        return {}

def generate_packing_suggestions(themes: Dict[str, int], preferences: List[str]) -> List[str]:
    """Generate packing suggestions based on themes and preferences."""
    suggestions = []
    
    # Weather-related suggestions
    if "outdoor" in themes:
        suggestions.append("Pack comfortable walking shoes")
        suggestions.append("Bring sunscreen and a hat")
    if "indoor" in themes:
        suggestions.append("Pack layers for temperature-controlled environments")
        
    # Activity-specific suggestions
    if "museum" in themes:
        suggestions.append("Bring a small notebook for notes")
    if "shopping" in themes:
        suggestions.append("Pack an extra bag for purchases")
        
    # Preference-based suggestions
    if "photography" in preferences:
        suggestions.append("Bring camera and extra memory cards")
    if "hiking" in preferences:
        suggestions.append("Pack hiking boots and a water bottle")
        
    return suggestions

def generate_local_tips(places: List[Dict[str, Any]]) -> List[str]:
    """Generate local tips based on place reviews."""
    tips = set()
    
    for place in places:
        insights = place.get('reviews', {}).get('analysis', {})
        precautions = insights.get('precautions', [])
        
        for precaution in precautions:
            if "local" in precaution.lower():
                tips.add(precaution)
                
    return list(tips)

def collect_safety_precautions(places: List[Dict[str, Any]]) -> List[str]:
    """Collect safety precautions from place reviews."""
    precautions = set()
    
    for place in places:
        insights = place.get('reviews', {}).get('analysis', {})
        place_precautions = insights.get('precautions', [])
        
        for precaution in place_precautions:
            if any(word in precaution.lower() for word in ['safety', 'security', 'caution', 'warning']):
                precautions.add(precaution)
                
    return list(precautions)

def generate_budget_tips(places: List[Dict[str, Any]]) -> List[str]:
    """Generate budget tips based on place prices and reviews."""
    tips = []
    
    # Calculate average price
    prices = [place.get('price', 0) for place in places if place.get('price', 0) > 0]
    if prices:
        avg_price = sum(prices) / len(prices)
        
        if avg_price > 50:
            tips.append("Consider purchasing attraction passes for discounts")
        if any(place.get('price', 0) > 100 for place in places):
            tips.append("Look for free activities on certain days")
            
    return tips

def suggest_alternatives(places: List[Dict[str, Any]], preferences: List[str]) -> List[Dict[str, Any]]:
    """Suggest alternative activities based on preferences."""
    alternatives = []
    
    # Get all available categories
    categories = set(place.get('category') for place in places)
    
    # Find places not in current itinerary
    current_place_ids = set(place.get('place_id') for place in places)
    
    for category in categories:
        # Get alternative places in same category
        alternative_places = [
            place for place in places
            if place.get('category') == category
            and place.get('place_id') not in current_place_ids
        ]
        
        if alternative_places:
            # Sort by rating and reviews
            alternative_places.sort(
                key=lambda x: (
                    x.get('rating', 0),
                    x.get('reviews', {}).get('average_rating', 0)
                ),
                reverse=True
            )
            
            # Add top alternative
            alternatives.append(alternative_places[0])
            
    return alternatives 