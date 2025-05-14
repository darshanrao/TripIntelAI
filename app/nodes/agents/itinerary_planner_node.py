from typing import Dict, Any, List, Optional, TypedDict, Set
import os
import json
from langchain_anthropic import ChatAnthropic
from app.schemas.trip_schema import TripMetadata
from app.utils.logger import logger
import re
from datetime import datetime, timedelta

DAILY_PLANNER_PROMPT = """You are a daily itinerary planner. Create a detailed schedule for day {current_day} of a {total_days}-day trip to {destination}.

Previous days' activities:
{previous_days}

Trip Information:
- Day of trip: {current_day} of {total_days}
- Destination: {destination}
- Start Date: {start_date}
- Current Day Date: {current_day_date}
- Flights: {flights}
- Hotel: {hotel}
- Budget constraints: {budget}

Available places to visit (not yet visited):
{available_places}

Available restaurants (not yet visited):
{available_restaurants}

Already visited places: {visited_places}
Already visited restaurants: {visited_restaurants}

Create a schedule that:
1. For day 1: Start with flight arrival and hotel check-in
2. For the last day: Include hotel check-out and flight departure
3. Groups nearby activities together
4. Includes meals at appropriate times (breakfast, lunch, dinner)
5. Stays within budget
6. Avoids revisiting places from previous days

Return the schedule as a JSON object in EXACTLY this format:
{{
  "date": "{current_day_date}",
  "activities": [
    {{
      "type": "accommodation|dining|attraction|transportation",
      "category": "hotel|breakfast|lunch|dinner|museum|park|theme park|flight|etc",
      "title": "Name of the activity",
      "time": "HH:MM",
      "duration_minutes": duration_in_minutes,
      "details": {{
        "location": "Full address if available",
        "latitude": latitude_if_available,
        "longitude": longitude_if_available
      }},
      "review_insights": {{
        "sentiment": "positive|neutral|negative",
        "strengths": [],
        "weaknesses": [],
        "summary": "Brief summary"
      }}
    }}
  ]
}}

IMPORTANT:
1. For each activity, if it's an attraction or restaurant, copy the location details (location, latitude, longitude) from the corresponding place in available_places or available_restaurants.
2. For flights and hotel activities, leave the details object empty.
3. Make sure to include appropriate activities for the time of day (morning, afternoon, evening).
4. Leave the review_insights fields as empty objects/arrays.
5. You MUST use the exact date provided in current_day_date for this day's itinerary.
"""

class GraphState(TypedDict):
    """State for the LangGraph pipeline."""
    current_day: int
    total_days: int
    destination: str
    start_date: str
    flights: List[Dict[str, Any]]
    places: List[Dict[str, Any]]
    restaurants: List[Dict[str, Any]]
    hotel: Dict[str, Any]
    budget: Dict[str, Any]
    route: Dict[str, Any]
    daily_itineraries: List[Dict[str, Any]]
    visited_places: Set[str]
    visited_restaurants: Set[str]
    final_itinerary: Optional[Dict[str, Any]]

async def itinerary_planner_node(state: GraphState) -> GraphState:
    """
    Create a daily itinerary based on available options and constraints.
    Uses prompt chaining to build the itinerary day by day.
    
    Args:
        state: Current state containing all necessary information
        
    Returns:
        Updated state with the new daily itinerary
    """
    try:
        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            error_msg = "ANTHROPIC_API_KEY not found in environment variables"
            logger.error(error_msg)
            state['error'] = error_msg
            return state
            
        # Strip any whitespace or newlines
        api_key = api_key.strip()
        
        # Initialize LLM
        llm = ChatAnthropic(
            api_key=api_key,
            model="claude-3-haiku-20240307",
            temperature=0.2,
            max_tokens=1000
        )
        
        # Get previous days' activities
        previous_days = state.get('daily_itineraries', [])
        
        # Calculate current day's date
        start_date = datetime.strptime(state.get('start_date', ''), '%Y-%m-%d')
        current_day_date = (start_date + timedelta(days=state.get('current_day', 1) - 1)).strftime('%Y-%m-%d')
        
        # Filter out already visited places and restaurants
        available_places = [
            place for place in state.get('places', [])
            if place.get('name') not in state.get('visited_places', set())
        ]
        
        available_restaurants = [
            restaurant for restaurant in state.get('restaurants', [])
            if restaurant.get('name') not in state.get('visited_restaurants', set())
        ]
        
        # Use Claude to create the daily schedule
        response = await llm.ainvoke(
            DAILY_PLANNER_PROMPT.format(
                current_day=state.get('current_day', 1),
                total_days=state.get('total_days', 1),
                destination=state.get('destination', 'Unknown'),
                start_date=state.get('start_date', ''),
                current_day_date=current_day_date,
                flights=state.get('flights', []),
                hotel=state.get('hotel', {}),
                budget=state.get('budget', {}),
                available_places=available_places,
                available_restaurants=available_restaurants,
                visited_places=list(state.get('visited_places', set())),
                visited_restaurants=list(state.get('visited_restaurants', set())),
                previous_days=previous_days
            )
        )
        
        # Parse the response
        content = response.content
        
        # Try multiple methods to extract and parse JSON
        daily_itinerary = None
        json_errors = []
        
        # Method 1: Find JSON between curly braces
        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_content = content[json_start:json_end]
                daily_itinerary = json.loads(json_content)
        except json.JSONDecodeError as e:
            json_errors.append(f"Method 1 failed: {str(e)}")
        
        # Method 2: Look for JSON in code blocks
        if not daily_itinerary:
            try:
                if "```json" in content:
                    json_content = content.split("```json")[1].split("```")[0].strip()
                    daily_itinerary = json.loads(json_content)
                elif "```" in content:
                    json_content = content.split("```")[1].split("```")[0].strip()
                    daily_itinerary = json.loads(json_content)
            except json.JSONDecodeError as e:
                json_errors.append(f"Method 2 failed: {str(e)}")
        
        # Method 3: Try to clean and fix common JSON issues
        if not daily_itinerary:
            try:
                # Remove any text before the first { and after the last }
                cleaned_content = content[content.find('{'):content.rfind('}')+1]
                # Fix common JSON formatting issues
                cleaned_content = cleaned_content.replace("'", '"')  # Replace single quotes
                cleaned_content = re.sub(r',\s*}', '}', cleaned_content)  # Remove trailing commas
                cleaned_content = re.sub(r',\s*]', ']', cleaned_content)  # Remove trailing commas in arrays
                daily_itinerary = json.loads(cleaned_content)
            except json.JSONDecodeError as e:
                json_errors.append(f"Method 3 failed: {str(e)}")
        
        if not daily_itinerary:
            error_msg = f"Could not parse JSON from response. Errors: {'; '.join(json_errors)}"
            logger.error(error_msg)
            state['error'] = error_msg
            return state
        
        # Validate the parsed JSON structure
        required_fields = ['date', 'activities']
        missing_fields = [field for field in required_fields if field not in daily_itinerary]
        if missing_fields:
            error_msg = f"Missing required fields in itinerary: {', '.join(missing_fields)}"
            logger.error(error_msg)
            state['error'] = error_msg
            return state
        
        # Ensure activities is a list
        if not isinstance(daily_itinerary.get('activities'), list):
            daily_itinerary['activities'] = []
        
        # Update visited places and restaurants from activities
        for activity in daily_itinerary.get('activities', []):
            if activity.get('type') == 'attraction':
                state['visited_places'].add(activity.get('title', ''))
            elif activity.get('type') == 'dining':
                state['visited_restaurants'].add(activity.get('title', ''))
        
        # Format the date properly
        day_num = state.get('current_day', 1)
        
        # Add to daily itineraries
        state['daily_itineraries'].append(daily_itinerary)
        
        # Update final itinerary
        if not state.get('final_itinerary'):
            # Calculate end date from start date and duration
            start_date = datetime.strptime(state.get('start_date', ''), '%Y-%m-%d')
            end_date = start_date + timedelta(days=state.get('total_days', 1) - 1)
            
            state['final_itinerary'] = {
                'trip_summary': {
                    'destination': state.get('destination', 'Unknown'),
                    'start_date': state.get('start_date', ''),
                    'end_date': end_date.strftime('%Y-%m-%d'),  # Set the calculated end date
                    'duration_days': state.get('total_days', 1),
                    'total_budget': 0
                },
                'daily_itinerary': {},
                'review_highlights': {
                    'top_rated_places': [],
                    'top_rated_restaurants': [],
                    'hotel_review_summary': {
                        'name': state.get('hotel', {}).get('name', ''),
                        'rating': state.get('hotel', {}).get('rating', 0),
                        'strengths': [],
                        'weaknesses': [],
                        'summary': ''
                    },
                    'overall': [],
                    'accommodations': [],
                    'dining': [],
                    'attractions': []
                }
            }
        
        # Add this day's itinerary to final itinerary
        state['final_itinerary']['daily_itinerary'][f'day_{day_num}'] = daily_itinerary
        
        # Increment current day
        state['current_day'] += 1
        
        return state
        
    except Exception as e:
        state['error'] = f"Failed to create daily itinerary: {str(e)}"
        logger.error(f"Failed to create daily itinerary: {str(e)}")
        return state 