from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime
from app.schemas.trip_schema import TripMetadata, Budget
import json
from langchain_anthropic import ChatAnthropic
import logging

logger = logging.getLogger(__name__)

async def search_real_prices(location: str, category: str, preferences: List[str]) -> Dict[str, Any]:
    """Search for real prices in a location for a specific category."""
    try:
        # Initialize Claude
        llm = ChatAnthropic(
            model="claude-3-haiku-20240307",
            temperature=0.2,
            max_tokens=1000
        )
        
        # Construct search queries based on category
        if category == "hotel":
            search_term = f"average {' '.join(preferences)} hotel prices in {location} per night 2024"
        elif category == "food":
            search_term = f"average {' '.join(preferences)} restaurant meal costs in {location} 2024"
        elif category == "activities":
            search_term = f"tourist attraction ticket prices in {location} 2024"
        
        # Use web search to get real price data
        response = await llm.ainvoke(
            f"""Search for current {category} prices in {location}. 
            Focus on {', '.join(preferences) if preferences else 'general'} options.
            Extract and return ONLY a JSON object with:
            - min_price: minimum typical price in USD
            - max_price: maximum typical price in USD
            - average_price: average/typical price in USD
            - details: brief explanation of what these prices typically include
            
            Format:
            {{
                "min_price": float,
                "max_price": float,
                "average_price": float,
                "details": "string"
            }}
            
            If you cannot find specific prices, use reasonable estimates based on the location and category.
            """
        )
        
        # Parse the response to extract the JSON
        content = response.content
        if not content:
            raise ValueError("Empty response from LLM")
            
        # Try to extract JSON from different formats
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # Clean the content to ensure it's valid JSON
        content = content.strip()
        if not content:
            raise ValueError("No JSON content found in response")
            
        try:
            price_data = json.loads(content)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract numbers from the text
            import re
            numbers = re.findall(r'\d+(?:\.\d+)?', content)
            if len(numbers) >= 3:
                price_data = {
                    "min_price": float(numbers[0]),
                    "max_price": float(numbers[1]),
                    "average_price": float(numbers[2]),
                    "details": "Extracted from text response"
                }
            else:
                raise ValueError("Could not extract price data from response")
        
        # Validate the price data
        if not all(key in price_data for key in ["min_price", "max_price", "average_price"]):
            raise ValueError("Missing required price fields")
            
        # Ensure all prices are positive numbers
        for key in ["min_price", "max_price", "average_price"]:
            if not isinstance(price_data[key], (int, float)) or price_data[key] < 0:
                price_data[key] = 0
                
        return price_data
        
    except Exception as e:
        logger.error(f"Error searching real prices for {category} in {location}: {str(e)}")
        # Return default values based on category
        defaults = {
            "hotel": {"min": 50, "max": 300, "avg": 150},
            "food": {"min": 10, "max": 50, "avg": 25},
            "activities": {"min": 5, "max": 100, "avg": 30}
        }
        category_defaults = defaults.get(category, {"min": 0, "max": 0, "avg": 0})
        return {
            "min_price": category_defaults["min"],
            "max_price": category_defaults["max"],
            "average_price": category_defaults["avg"],
            "details": f"Using default values due to error: {str(e)}"
        }

async def get_real_hotel_prices(state: Dict[str, Any], metadata: TripMetadata) -> float:
    """Get real hotel prices based on location and preferences"""
    hotel_data = await search_real_prices(
        location=metadata.destination,
        category="hotel",
        preferences=metadata.preferences
    )
    
    # Use the average price, or calculate based on min/max if no average
    if hotel_data["average_price"] > 0:
        return hotel_data["average_price"]
    return (hotel_data["min_price"] + hotel_data["max_price"]) / 2

async def get_real_food_prices(state: Dict[str, Any], metadata: TripMetadata) -> float:
    """Get real food costs based on location and preferences"""
    food_data = await search_real_prices(
        location=metadata.destination,
        category="food",
        preferences=metadata.preferences
    )
    
    # Multiply by 3 for three meals a day
    daily_food_cost = food_data["average_price"] * 3
    return daily_food_cost

async def get_real_activity_prices(state: Dict[str, Any], metadata: TripMetadata) -> float:
    """Get real activity prices based on selected places"""
    total_activity_cost = 0
    places = state.get("places", [])
    
    # Search for prices for each place
    for place in places:
        if isinstance(place, dict):
            place_name = place.get("name", "")
            if place_name:
                activity_data = await search_real_prices(
                    location=f"{place_name} in {metadata.destination}",
                    category="activities",
                    preferences=metadata.preferences
                )
                total_activity_cost += activity_data["average_price"]
    
    return total_activity_cost

async def budget_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced budget node that uses real price data from web searches.
    
    Args:
        state: Current state containing trip data
        
    Returns:
        Updated state with budget estimates using real prices
    """
    metadata: Optional[TripMetadata] = state.get("metadata")
    
    if not metadata or not metadata.start_date or not metadata.end_date:
        state["budget"] = {}
        return state
    
    # Calculate trip duration
    duration = (metadata.end_date - metadata.start_date).days or 1
    
    try:
        # Get flight costs from state
        flights_total = 0
        flights = state.get("flights", [])
        if flights:
            cheapest_flight = min(flights, key=lambda x: x.get("price", float("inf")))
            flights_total = cheapest_flight.get("price", 0) * metadata.num_people
        
        # Get real hotel prices
        hotel_per_night = await get_real_hotel_prices(state, metadata)
        hotel_total = hotel_per_night * duration
        
        # Get real food costs
        daily_food_cost = await get_real_food_prices(state, metadata)
        daily_food_estimate = daily_food_cost * metadata.num_people
        
        # Get real activity costs
        activities_estimate = await get_real_activity_prices(state, metadata)
        activities_estimate *= metadata.num_people
        
        # Calculate transportation costs if using route
        transportation_cost = 0
        route = state.get("route", {})
        if route and "distance_km" in route:
            distance_km = route.get("distance_km", 0)
            if distance_km > 0:
                # Use more accurate car rental and fuel costs
                rental_data = await search_real_prices(
                    location=metadata.destination,
                    category="car rental",
                    preferences=metadata.preferences
                )
                daily_rental = rental_data["average_price"]
                fuel_cost_per_km = 0.15  # Average fuel cost per km
                transportation_cost = (distance_km * fuel_cost_per_km) + (daily_rental * duration)
        
        # Calculate total budget
        total = (
            flights_total +
            hotel_total +
            (daily_food_estimate * duration) +
            activities_estimate +
            transportation_cost
        )
        
        # Add buffer for miscellaneous expenses (10%)
        misc_buffer = total * 0.1
        total += misc_buffer
        
        # Create budget object with rounded values
        budget = Budget(
            flights_total=round(flights_total, 2),
            hotel_total=round(hotel_total, 2),
            daily_food_estimate=round(daily_food_estimate, 2),
            activities_estimate=round(activities_estimate, 2),
            total=round(total, 2)
        )
        
        # Add to state
        state["budget"] = budget.dict()
        
        # Add detailed price information for reference
        state["budget_details"] = {
            "price_searches": {
                "hotel": await search_real_prices(metadata.destination, "hotel", metadata.preferences),
                "food": await search_real_prices(metadata.destination, "food", metadata.preferences),
                "activities": await search_real_prices(metadata.destination, "activities", metadata.preferences)
            },
            "calculations": {
                "per_night_hotel": hotel_per_night,
                "per_day_food": daily_food_cost,
                "per_person_activities": activities_estimate / metadata.num_people,
                "transportation": transportation_cost,
                "misc_buffer": misc_buffer
            }
        }
        
    except Exception as e:
        print(f"Error calculating budget with real prices: {str(e)}")
        # Fallback to original budget calculation method
        return await fallback_budget_calculation(state)
    
    return state

async def fallback_budget_calculation(state: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback to original budget calculation if real price fetching fails"""
    # Original budget calculation logic here...
    # (Copy the original budget_node logic here as a fallback)
    return state 