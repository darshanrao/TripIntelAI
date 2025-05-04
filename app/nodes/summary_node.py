from typing import Dict, Any, TypedDict, Optional, List
from datetime import datetime, timedelta
import json
import asyncio
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from app.schemas.trip_schema import TripMetadata

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
            // All relevant details from the provided data 
            // For flights: airline, flight_number, departure_time, arrival_time, price
            // For hotels: name, location, rating, price_per_night, amenities
            // For attractions: name, description, location, rating, price
            // For dining: name, cuisine, location, rating, price_level, description
          }}
        }},
        // More activities...
      ]
    }},
    // More days...
  }}
}}

IMPORTANT: Your output MUST be a valid JSON object. Do not include any explanations, markdown, or text outside the JSON structure.
"""

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
            itinerary = json.loads(json_str)
            state["itinerary"] = itinerary
        except json.JSONDecodeError:
            # Fallback to simple itinerary if JSON parsing fails
            state["itinerary"] = {
                "error": "Failed to parse generated itinerary",
                "raw_response": response_content
            }
            
    except Exception as e:
        # Handle any errors that occur during Claude API call
        state["itinerary"] = {
            "error": f"Error generating itinerary: {str(e)}"
        }
        print(f"Error in Claude API call: {e}")
    
    return state 