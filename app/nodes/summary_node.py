from typing import Dict, Any, TypedDict, Optional, List
from datetime import datetime, timedelta
import json
import asyncio
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from app.schemas.trip_schema import TripMetadata
from app.nodes.location_coordinates import LocationCoordinates

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
    itinerary: Dict[str, Any]
    error: Optional[str]

def datetime_to_str(obj):
    """Convert datetime objects to strings for JSON serialization."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

ITINERARY_PROMPT = """
You are an expert travel planner. Your task is to create a detailed, day-by-day itinerary for a trip based on the data provided.

Trip Metadata:
{metadata}

Available Flights:
{flights}

Hotel Information:
{hotel}

Places to Visit:
{places}

Restaurants:
{restaurants}

Budget Information:
{budget}

Transportation/Route Information:
{route}

INSTRUCTIONS:
1. Create a daily itinerary for each day of the trip (from start_date to end_date)
2. Allocate activities (flights, hotel check-in/out, attractions, meals) to specific days and times
3. Be realistic about timing - account for travel time between locations, meal duration, etc.
4. Assign specific restaurants for meals based on their location and the day's activities
5. Include arrival and departure flights on the appropriate days
6. Include hotel check-in on the first day and check-out on the last day
7. Incorporate review insights for places, restaurants, and hotels to highlight key strengths and precautions

IMPORTANT: 
- Keep your response concise and focused on essential information
- Limit review insights to 1-2 key points each
- Keep descriptions brief and to the point
- Focus on the most important activities and details

OUTPUT FORMAT:
Return your response ONLY as a valid JSON object with the following structure:
{{
  "trip_summary": {{
    "destination": "destination_name",
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "duration_days": number,
    "total_budget": number
  }},
  "daily_itinerary": {{
    "day_1": {{
      "date": "YYYY-MM-DD",
      "activities": [
        {{
          "type": "transportation|accommodation|attraction|dining",
          "category": "flight|hotel|landmark|museum|lunch|dinner|etc",
          "title": "descriptive title",
          "time": "HH:MM",
          "duration_minutes": number,
          "details": {{
            // Essential details only
          }},
          "review_insights": {{
            // Only include if review insights are available
            "sentiment": "positive/negative/neutral",
            "strengths": ["key strength"],
            "weaknesses": ["key weakness"],
            "summary": "1-2 sentence summary"
          }}
        }}
      ]
    }}
  }},
  "review_highlights": {{
    "top_rated_places": [
      {{
        "name": "place_name",
        "rating": number,
        "key_strength": "main strength",
        "summary": "1 sentence"
      }}
    ],
    "top_rated_restaurants": [
      {{
        "name": "restaurant_name",
        "rating": number,
        "key_strength": "main strength",
        "summary": "1 sentence"
      }}
    ],
    "hotel_review_summary": {{
      "name": "hotel_name",
      "rating": number,
      "key_strength": "main strength",
      "key_weakness": "main weakness",
      "summary": "1 sentence"
    }}
  }}
}}

IMPORTANT: Your output MUST be a valid JSON object. Do not include any explanations, markdown, or text outside the JSON structure.
"""

def merge_review_insights(itinerary: Dict[str, Any], state: GraphState) -> Dict[str, Any]:
    """
    Merge review insights from the state into the itinerary.
    Only includes reviews for places that are actually in the itinerary.
    
    Args:
        itinerary: The generated itinerary
        state: The current state containing review insights
        
    Returns:
        Updated itinerary with merged review insights
    """
    if not isinstance(itinerary, dict):
        return itinerary
        
    # Get review data from state
    places = state.get("places", [])
    restaurants = state.get("restaurants", [])
    hotel = state.get("hotel", {})
    
    # Track which places and restaurants are actually in the itinerary
    itinerary_places = set()
    itinerary_restaurants = set()
    
    # Add review insights to each activity in the itinerary
    if "daily_itinerary" in itinerary:
        for day_key, day_data in itinerary["daily_itinerary"].items():
            if "activities" in day_data:
                for activity in day_data["activities"]:
                    # Skip if no details or name
                    if "details" not in activity or "name" not in activity["details"]:
                        continue
                        
                    activity_name = activity["details"]["name"]
                    
                    # Add review insights for places
                    if activity["type"] == "attraction":
                        place = next((p for p in places if p.get("name") == activity_name), None)
                        if place and place.get("review_insights"):
                            activity["review_insights"] = place["review_insights"]
                            itinerary_places.add(activity_name)
                    
                    # Add review insights for restaurants
                    elif activity["type"] == "dining":
                        restaurant = next((r for r in restaurants if r.get("name") == activity_name), None)
                        if restaurant and restaurant.get("review_insights"):
                            activity["review_insights"] = restaurant["review_insights"]
                            itinerary_restaurants.add(activity_name)
                    
                    # Add review insights for hotel
                    elif activity["type"] == "accommodation" and hotel.get("review_insights"):
                        activity["review_insights"] = hotel["review_insights"]
    
    # Add review highlights section
    itinerary["review_highlights"] = {}
    
    # Add top rated places (only those in the itinerary)
    if places:
        top_places = sorted(
            [p for p in places if p.get("review_insights") and p.get("name") in itinerary_places],
            key=lambda x: x.get("rating", 0),
            reverse=True
        )[:3]
        itinerary["review_highlights"]["top_rated_places"] = [
            {
                "name": p.get("name", ""),
                "rating": p.get("rating", 0),
                "strengths": p.get("review_insights", {}).get("analysis", {}).get("strengths", []),
                "weaknesses": p.get("review_insights", {}).get("analysis", {}).get("weaknesses", []),
                "summary": p.get("review_insights", {}).get("analysis", {}).get("summary", "")
            }
            for p in top_places
        ]
    
    # Add top rated restaurants (only those in the itinerary)
    if restaurants:
        top_restaurants = sorted(
            [r for r in restaurants if r.get("review_insights") and r.get("name") in itinerary_restaurants],
            key=lambda x: x.get("rating", 0),
            reverse=True
        )[:3]
        itinerary["review_highlights"]["top_rated_restaurants"] = [
            {
                "name": r.get("name", ""),
                "rating": r.get("rating", 0),
                "strengths": r.get("review_insights", {}).get("analysis", {}).get("strengths", []),
                "weaknesses": r.get("review_insights", {}).get("analysis", {}).get("weaknesses", []),
                "summary": r.get("review_insights", {}).get("analysis", {}).get("summary", "")
            }
            for r in top_restaurants
        ]
    
    # Add hotel review summary (only if hotel is in the itinerary)
    if hotel and hotel.get("review_insights"):
        # Check if hotel is in the itinerary
        hotel_in_itinerary = False
        if "daily_itinerary" in itinerary:
            for day_data in itinerary["daily_itinerary"].values():
                if "activities" in day_data:
                    for activity in day_data["activities"]:
                        if activity.get("type") == "accommodation":
                            hotel_in_itinerary = True
                            break
                if hotel_in_itinerary:
                    break
        
        if hotel_in_itinerary:
            itinerary["review_highlights"]["hotel_review_summary"] = {
                "name": hotel.get("name", ""),
                "rating": hotel.get("rating", 0),
                "strengths": hotel.get("review_insights", {}).get("analysis", {}).get("strengths", []),
                "weaknesses": hotel.get("review_insights", {}).get("analysis", {}).get("weaknesses", []),
                "summary": hotel.get("review_insights", {}).get("analysis", {}).get("summary", "")
            }
    
    return itinerary

async def summary_node(state: GraphState) -> GraphState:
    """
    Generate a daily itinerary JSON from the trip data using Claude.
    
    Args:
        state: The current state containing trip data from previous nodes
        
    Returns:
        Dict containing the formatted itinerary as a JSON structure
    """
    # Extract metadata from state
    metadata = state.get("metadata", {})
    
    # Check if metadata exists and has required fields
    if not metadata:
        state["itinerary"] = {"error": "Missing trip metadata"}
        return state
    
    # Handle both Pydantic model and dictionary formats
    if hasattr(metadata, 'model_dump'):
        # It's a Pydantic model
        metadata_dict = metadata.model_dump()
        start_date = metadata.start_date
        end_date = metadata.end_date
    elif hasattr(metadata, 'dict'):
        # Older Pydantic versions
        metadata_dict = metadata.dict()
        start_date = metadata.start_date
        end_date = metadata.end_date
    else:
        # It's a dictionary
        metadata_dict = metadata
        start_date = metadata.get("start_date")
        end_date = metadata.get("end_date")
    
    # Check if dates exist
    if not start_date or not end_date:
        state["itinerary"] = {"error": "Missing trip dates in metadata"}
        return state
    
    # Prepare data for the prompt
    flights = state.get("flights", [])
    hotel = state.get("hotel", {})
    places = state.get("places", [])
    restaurants = state.get("restaurants", [])
    budget = state.get("budget", {})
    route = state.get("route", {})
    
    # Format data for the prompt
    prompt_data = {
        "metadata": json.dumps(metadata_dict, default=datetime_to_str),
        "flights": json.dumps(flights, default=datetime_to_str),
        "hotel": json.dumps(hotel, default=datetime_to_str),
        "places": json.dumps(places, default=datetime_to_str),
        "restaurants": json.dumps(restaurants, default=datetime_to_str),
        "budget": json.dumps(budget, default=datetime_to_str),
        "route": json.dumps(route, default=datetime_to_str)
    }
    
    # Initialize Claude
    llm = ChatAnthropic(
        model="claude-3-sonnet-20240229",
        temperature=0.2,
        max_tokens=4000
    )
    
    # Build the prompt
    formatted_prompt = ITINERARY_PROMPT.format(**prompt_data)
    
    # Call Claude to generate the itinerary
    try:
        response = await llm.ainvoke(
            [HumanMessage(content=formatted_prompt)]
        )
        
        # Extract and parse JSON from response
        response_content = response.content
        
        # Extract JSON if it's embedded in text
        if '```json' in response_content:
            json_start = response_content.find('```json') + 7
            json_end = response_content.find('```', json_start)
            json_str = response_content[json_start:json_end].strip()
        elif '```' in response_content:
            json_start = response_content.find('```') + 3
            json_end = response_content.find('```', json_start)
            json_str = response_content[json_start:json_end].strip()
        else:
            json_str = response_content.strip()
        
        # Parse the JSON
        try:
            # First try to parse the complete JSON
            itinerary = json.loads(json_str)
            
            # If parsing succeeds but the JSON is incomplete, try to fix it
            if not isinstance(itinerary, dict) or not itinerary.get("daily_itinerary"):
                # Try to find the last complete JSON object
                last_brace = json_str.rfind("}")
                if last_brace != -1:
                    json_str = json_str[:last_brace + 1]
                    itinerary = json.loads(json_str)
            
            # Get all places from the itinerary and their activities
            places_to_process = []
            if "daily_itinerary" in itinerary:
                for day_data in itinerary["daily_itinerary"].values():
                    if "activities" in day_data:
                        for activity in day_data["activities"]:
                            # Get coordinates for all types of activities that have a location
                            if "details" in activity:
                                # Try to get the place name from either 'name' or 'location'
                                place_name = activity["details"].get("name") or activity["details"].get("location")
                                if place_name:  # Only add if name exists
                                    places_to_process.append((activity, place_name))
            
            # Get coordinates for places in the itinerary
            if places_to_process:
                location_coords = LocationCoordinates()
                for activity, place_name in places_to_process:
                    try:
                        coords = await location_coords.get_coordinates(place_name)
                        if coords:
                            activity["details"]["coordinates"] = coords
                    except Exception as e:
                        print(f"Error getting coordinates for {place_name}: {str(e)}")
            
            # Merge review insights with the itinerary
            itinerary = merge_review_insights(itinerary, state)
            
            state["itinerary"] = itinerary
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {str(e)}")
            print(f"JSON string length: {len(json_str)}")
            print(f"JSON string preview: {json_str[:200]}...")
            
            # Try to fix common JSON issues
            try:
                # Remove any trailing commas
                json_str = json_str.replace(",\n}", "\n}")
                json_str = json_str.replace(",\n  }", "\n  }")
                
                # Try parsing again
                itinerary = json.loads(json_str)
                # Merge review insights with the itinerary
                itinerary = merge_review_insights(itinerary, state)
                state["itinerary"] = itinerary
            except json.JSONDecodeError:
                # If still failing, return error with more context
                state["itinerary"] = {
                    "error": "Failed to parse generated itinerary",
                    "raw_response": response_content[:1000] + "..." if len(response_content) > 1000 else response_content,
                    "json_error": str(e)
                }
            
    except Exception as e:
        # Handle any errors that occur during Claude API call
        print(f"Error in Claude API call: {str(e)}")
        print(f"Error type: {type(e)}")
        state["itinerary"] = {
            "error": f"Error generating itinerary: {str(e)}"
        }
    
    return state 