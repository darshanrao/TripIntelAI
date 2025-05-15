# Standard library imports
import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, TypedDict, Set
import asyncio

# Third-party imports
import httpx
from langchain_anthropic import ChatAnthropic

# Local imports
from app.schemas.trip_schema import TripMetadata
from app.utils.logger import logger
from app.utils.gemini_client import get_gemini_response

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
        "location": "",
        "latitude": null,
        "longitude": null
      }},
      "review_insights": {{
        "sentiment": "",
        "strengths": [],
        "weaknesses": [],
        "summary": ""
      }}
    }}
  ]
}}

IMPORTANT:
1. Leave the details and review_insights objects empty but maintain their structure.
2. For flights and hotel activities, keep the details object empty.
3. Make sure to include appropriate activities for the time of day (morning, afternoon, evening).
4. You MUST use the exact date provided in current_day_date for this day's itinerary.
5. Ensure proper JSON formatting:
   - Use double quotes for all strings
   - Include commas between all array elements and object properties
   - Do not include trailing commas
   - Ensure all arrays and objects are properly closed
   - Validate that the JSON is properly formatted before returning
6. Return ONLY the JSON object, with no additional text or explanation.
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

class PerplexityActivityDetails:
    def __init__(self, api_key: str):
        self.api_key = api_key.strip().strip('"\'')
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        logger.info(f"Initialized PerplexityActivityDetails with API key: {self.api_key[:8]}...")
        
    async def get_activity_details(
        self,
        activity_type: str,
        activity_title: str,
        location: str
    ) -> Dict[str, Any]:
        """Get activity details using Perplexity API with retry logic"""
        if not all([activity_type, activity_title, location]):
            logger.error("Missing required parameters for activity details")
            return {}
            
        query = f"""For the following activity in {location}, provide detailed information in JSON format:

Activity: {activity_title}
Type: {activity_type}

Please provide:
1. The exact location (address) of this place
2. Its latitude and longitude coordinates
3. A summary of reviews and ratings from TripAdvisor, Google Reviews, and other travel sites
4. Key strengths and weaknesses from reviews
5. Overall sentiment based on reviews

Return the information in this exact JSON format:
{{
    "details": {{
        "location": "Full address",
        "latitude": latitude_as_float,
        "longitude": longitude_as_float
    }},
    "review_insights": {{
        "sentiment": "positive|neutral|negative",
        "strengths": ["strength1", "strength2", "strength3"],
        "weaknesses": ["weakness1", "weakness2"],
        "summary": "A detailed summary of reviews highlighting key points, ratings, and visitor experiences"
    }}
}}

IMPORTANT:
- For location, provide the complete address
- For coordinates, provide exact latitude and longitude as numbers
- For review insights:
  * sentiment must be one of: positive, neutral, negative
  * strengths must be a list of at least 2 specific positive points from reviews
  * weaknesses must be a list of at least 1 specific negative point from reviews
  * summary must be at least 50 words describing the overall experience
- Make sure all fields are filled with actual data, not placeholders
- Location must be a valid address in {location}
- Coordinates must be valid for {location}
- Review insights must be specific to this exact location"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "sonar",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a travel information expert. Provide accurate and detailed information about locations and their reviews. Always verify the information is specific to the exact location requested. For reviews, focus on recent visitor experiences and common themes in feedback."
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "temperature": 0.3
        }
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        self.base_url,
                        json=data,
                        headers=headers,
                        timeout=30.0
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"Perplexity API error (attempt {attempt + 1}/{self.max_retries}): Status {response.status_code}, Response: {response.text}")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delay)
                            continue
                        return {}
                    
                    result = response.json()
                    if not result.get("choices") or not result["choices"][0].get("message", {}).get("content"):
                        logger.error(f"Invalid response format (attempt {attempt + 1}/{self.max_retries})")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delay)
                            continue
                        return {}
                        
                    content = result["choices"][0]["message"]["content"]
                    logger.info(f"Received response for {activity_title}: {content}")
                    
                    try:
                        json_start = content.find('{')
                        json_end = content.rfind('}') + 1
                        if json_start >= 0 and json_end > json_start:
                            json_str = content[json_start:json_end]
                            parsed_data = json.loads(json_str)
                            
                            # Validate the structure
                            if not isinstance(parsed_data, dict):
                                logger.error("Invalid JSON structure: not a dictionary")
                                if attempt < self.max_retries - 1:
                                    await asyncio.sleep(self.retry_delay)
                                    continue
                                return {}
                                
                            if not all(key in parsed_data for key in ["details", "review_insights"]):
                                logger.error("Missing required fields in response")
                                if attempt < self.max_retries - 1:
                                    await asyncio.sleep(self.retry_delay)
                                    continue
                                return {}
                                
                            # Validate details
                            details = parsed_data.get("details", {})
                            if not self._validate_details(details, location):
                                logger.error("Invalid details data")
                                if attempt < self.max_retries - 1:
                                    await asyncio.sleep(self.retry_delay)
                                    continue
                                return {}
                                
                            # Validate review insights
                            review_insights = parsed_data.get("review_insights", {})
                            if not self._validate_review_insights(review_insights):
                                logger.error("Invalid review insights data")
                                if attempt < self.max_retries - 1:
                                    await asyncio.sleep(self.retry_delay)
                                    continue
                                return {}
                                
                            return parsed_data
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON from response: {e}")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delay)
                            continue
                        return {}
                    
            except httpx.HTTPError as e:
                logger.error(f"HTTP error occurred (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                return {}
            except Exception as e:
                logger.error(f"Unexpected error (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                return {}
                
        return {}
        
    def _validate_details(self, details: Dict[str, Any], location: str) -> bool:
        """Validate the details data"""
        if not details.get("location"):
            return False
            
        # Check if location contains the city name
        if location.lower() not in details["location"].lower():
            return False
            
        # Validate coordinates
        try:
            lat = float(details.get("latitude", 0))
            lon = float(details.get("longitude", 0))
            
            # Basic coordinate validation
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                return False
                
            # Additional validation for specific cities
            if location.lower() == "paris":
                if not (48.8 <= lat <= 48.9) or not (2.2 <= lon <= 2.4):
                    return False
                    
        except (ValueError, TypeError):
            return False
            
        return True
        
    def _validate_review_insights(self, review_insights: Dict[str, Any]) -> bool:
        """Validate the review insights data"""
        if not review_insights.get("sentiment") or review_insights["sentiment"] not in ["positive", "neutral", "negative"]:
            return False
            
        if not isinstance(review_insights.get("strengths"), list) or not isinstance(review_insights.get("weaknesses"), list):
            return False
            
        # Ensure we have enough strengths and weaknesses
        if len(review_insights.get("strengths", [])) < 2:
            return False
            
        if len(review_insights.get("weaknesses", [])) < 1:
            return False
            
        # Ensure summary is detailed enough
        if not review_insights.get("summary") or len(review_insights["summary"]) < 50:
            return False
            
        return True

async def populate_activity_details(state: GraphState) -> GraphState:
    """
    Populate details and review insights for activities in the daily itinerary.
    
    Args:
        state: Current state containing the daily itinerary
        
    Returns:
        Updated state with populated activity details
    """
    try:
        api_key = os.getenv("PERPLEXITY_API_KEY")
        if not api_key:
            logger.error("Perplexity API key not found")
            return state
            
        details_client = PerplexityActivityDetails(api_key=api_key)
        
        # Get the latest daily itinerary
        if not state.get('daily_itineraries'):
            logger.warning("No daily itineraries found to populate")
            return state
            
        latest_itinerary = state['daily_itineraries'][-1]
        if not latest_itinerary.get('activities'):
            logger.warning("No activities found in latest itinerary")
            return state
        
        # Track successful and failed updates
        successful_updates = 0
        failed_updates = 0
        
        # Log initial state
        logger.info(f"Starting to populate details for {len(latest_itinerary.get('activities', []))} activities")
        
        # Process each activity
        for activity in latest_itinerary.get('activities', []):
            activity_title = activity.get('title', 'Unknown')
            activity_type = activity.get('type', 'Unknown')
            
            # Skip flights and hotel activities
            if activity_type in ['transportation', 'accommodation']:
                logger.info(f"Skipping {activity_title} - type {activity_type} doesn't need details")
                continue
                
            # Check if we need to populate details or review insights
            needs_details = not activity.get('details', {}).get('location')
            needs_reviews = not activity.get('review_insights', {}).get('summary')
            
            if not needs_details and not needs_reviews:
                logger.info(f"Skipping {activity_title} - already has complete details and reviews")
                successful_updates += 1
                continue
                
            logger.info(f"Getting details for activity: {activity_title} (Type: {activity_type})")
            
            # Get details from Perplexity
            activity_details = await details_client.get_activity_details(
                activity_type=activity_type,
                activity_title=activity_title,
                location=state.get('destination', '')
            )
            
            # Update activity with details
            if activity_details:
                # Update details if needed
                if needs_details and 'details' in activity_details:
                    activity['details'] = {
                        'location': activity_details['details'].get('location', ''),
                        'latitude': activity_details['details'].get('latitude'),
                        'longitude': activity_details['details'].get('longitude')
                    }
                
                # Update review insights if needed
                if needs_reviews and 'review_insights' in activity_details:
                    activity['review_insights'] = {
                        'sentiment': activity_details['review_insights'].get('sentiment', ''),
                        'strengths': activity_details['review_insights'].get('strengths', []),
                        'weaknesses': activity_details['review_insights'].get('weaknesses', []),
                        'summary': activity_details['review_insights'].get('summary', '')
                    }
                successful_updates += 1
                logger.info(f"Successfully updated details for {activity_title}")
            else:
                logger.warning(f"Failed to get details for activity: {activity_title}")
                failed_updates += 1
        
        # Log summary of updates
        logger.info(f"Activity details update summary: {successful_updates} successful, {failed_updates} failed")
        
        # Update the daily itinerary in state
        state['daily_itineraries'][-1] = latest_itinerary
        
        return state
        
    except Exception as e:
        logger.error(f"Error populating activity details: {str(e)}")
        return state

def clean_json_string(json_str: str) -> str:
    """Clean and fix common JSON formatting issues."""
    # Remove any text before the first { and after the last }
    json_str = json_str[json_str.find('{'):json_str.rfind('}')+1]
    
    # Replace single quotes with double quotes
    json_str = json_str.replace("'", '"')
    
    # Fix missing commas between array elements
    json_str = re.sub(r'}\s*{', '},{', json_str)
    json_str = re.sub(r']\s*{', '],{', json_str)
    json_str = re.sub(r'"\s*{', '",{', json_str)
    
    # Remove trailing commas
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    # Fix missing commas between object properties
    json_str = re.sub(r'"\s*"', '","', json_str)
    
    # Fix missing quotes around property names
    json_str = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
    
    return json_str

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
        
        # Format the prompt
        prompt = DAILY_PLANNER_PROMPT.format(
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
        
        # Get response from Gemini
        content = await get_gemini_response(
            prompt=prompt,
            model="gemini-2.0-flash",
            max_tokens=1000
        )
        
        if not content:
            error_msg = "Failed to get response from Gemini"
            logger.error(error_msg)
            state['error'] = error_msg
            return state
        
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
                cleaned_content = clean_json_string(content)
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
        logger.info(f"Added initial daily itinerary for day {day_num}")
        
        # Populate activity details BEFORE adding to final itinerary
        logger.info("Starting to populate activity details...")
        state = await populate_activity_details(state)
        logger.info("Finished populating activity details")
        
        # Get the updated daily itinerary with populated details
        updated_daily_itinerary = state['daily_itineraries'][-1]
        logger.info("Verifying updated daily itinerary before adding to final structure:")
        logger.info(json.dumps(updated_daily_itinerary, indent=2))
        
        # Update final itinerary
        if not state.get('final_itinerary'):
            logger.info("Creating new final itinerary structure")
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
        
        # Add this day's itinerary to final itinerary with populated details
        state['final_itinerary']['daily_itinerary'][f'day_{day_num}'] = updated_daily_itinerary
        logger.info(f"Added day {day_num} itinerary to final structure")
        
        # Verify the final structure
        logger.info("Verifying final itinerary structure:")
        logger.info(json.dumps(state['final_itinerary']['daily_itinerary'][f'day_{day_num}'], indent=2))
        
        # Increment current day
        state['current_day'] += 1
        
        return state
        
    except Exception as e:
        state['error'] = f"Failed to create daily itinerary: {str(e)}"
        logger.error(f"Failed to create daily itinerary: {str(e)}")
        return state 