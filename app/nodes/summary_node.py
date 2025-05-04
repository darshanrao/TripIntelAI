from typing import Dict, Any, TypedDict, Optional, List, Set
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
    selected_flights: List[Dict[str, Any]]
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

class CircularReferenceEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles circular references and limits recursion depth.
    """
    def __init__(self, *args, **kwargs):
        self.max_depth = kwargs.pop('max_depth', 10)
        super().__init__(*args, **kwargs)
        self.visited_objects: Set[int] = set()
        self.current_depth = 0
        
    def default(self, obj):
        obj_id = id(obj)
        
        # Check for circular reference
        if obj_id in self.visited_objects:
            return f"CIRCULAR_REF"
        
        # Check depth limit
        if self.current_depth >= self.max_depth:
            if isinstance(obj, (list, tuple)):
                return f"[... {len(obj)} items ...]"
            elif isinstance(obj, dict):
                return f"{{... {len(obj)} keys ...}}"
            else:
                return str(obj)
        
        # Add this object to visited set and increment depth
        self.visited_objects.add(obj_id)
        self.current_depth += 1
        
        try:
            # Handle datetime objects
            if isinstance(obj, datetime):
                return obj.isoformat()
                
            # Handle Pydantic models
            if hasattr(obj, 'dict') and callable(getattr(obj, 'dict')):
                try:
                    return obj.dict()
                except Exception:
                    # Fallback for older Pydantic versions or errors
                    pass
                
            if hasattr(obj, 'model_dump') and callable(getattr(obj, 'model_dump')):
                try:
                    return obj.model_dump()
                except Exception:
                    # Fallback if model_dump fails
                    pass
            
            # Handle specific types that might have circular references
            if isinstance(obj, dict):
                return {str(k): v for k, v in obj.items()}
                
            if isinstance(obj, (list, tuple)):
                return list(obj)
                
            # Convert common types to simple representations
            if hasattr(obj, '__dict__'):
                try:
                    return {k: v for k, v in obj.__dict__.items() 
                           if not k.startswith('_')}
                except Exception:
                    return str(obj)
                
            # Use default behavior for other types
            return super().default(obj)
            
        except Exception as e:
            # If anything goes wrong, return a string representation
            return f"<Error: {str(e)}>"
            
        finally:
            # Remove from visited set and decrement depth after processing
            self.visited_objects.remove(obj_id)
            self.current_depth -= 1

def safe_json_dumps(obj, **kwargs) -> str:
    """
    Safely serialize an object to JSON string, handling circular references.
    
    Args:
        obj: Object to serialize
        **kwargs: Additional arguments to pass to json.dumps
        
    Returns:
        JSON string
    """
    try:
        return json.dumps(obj, cls=CircularReferenceEncoder, default=datetime_to_str, **kwargs)
    except (TypeError, OverflowError, ValueError) as e:
        print(f"Error during JSON serialization: {str(e)}")
        # Try again with a more aggressive approach
        try:
            # Convert to simple types first
            if isinstance(obj, dict):
                simplified = {str(k): str(v) if not isinstance(v, (dict, list)) else v 
                             for k, v in obj.items()}
            elif isinstance(obj, list):
                simplified = [str(item) if not isinstance(item, (dict, list)) else item 
                             for item in obj]
            else:
                simplified = str(obj)
                
            return json.dumps(simplified, cls=CircularReferenceEncoder, 
                             default=lambda o: str(o), **kwargs)
        except Exception:
            # Last resort - convert everything to string
            return json.dumps(str(obj))

ITINERARY_PROMPT = """
You are an expert travel planner. Your task is to create a detailed, day-by-day itinerary for a trip based on the data provided.

Trip Metadata:
{metadata}

Selected Flight:
{selected_flights}

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
5. Include the selected flight on the appropriate days - this is the flight the user has specifically chosen
6. Include hotel check-in on the first day and check-out on the last day
7. Incorporate review insights for places, restaurants, and hotels to highlight key strengths and precautions

IMPORTANT: 
- Keep your response concise and focused on essential information
- Limit review insights to 1-2 key points each
- Keep descriptions brief and to the point
- Focus on the most important activities and details
- Use the exact flight information provided as it represents the user's chosen flight

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

def generate_readable_itinerary(itinerary_data: Dict[str, Any], state: GraphState) -> str:
    """
    Convert the JSON itinerary data to a human-readable text format.
    
    Args:
        itinerary_data: The generated itinerary in JSON format
        state: The current state
        
    Returns:
        A formatted string with the itinerary
    """
    try:
        if not isinstance(itinerary_data, dict):
            print(f"WARNING: itinerary_data is not a dict but a {type(itinerary_data)}")
            return str(itinerary_data)
        
        output = []
        
        # Add trip summary
        if "trip_summary" in itinerary_data:
            try:
                summary = itinerary_data["trip_summary"]
                output.append("🗺️ TRIP SUMMARY")
                output.append("=" * 80)
                output.append(f"Destination: {summary.get('destination', 'Unknown')}")
                output.append(f"Dates: {summary.get('start_date', 'Unknown')} to {summary.get('end_date', 'Unknown')}")
                output.append(f"Duration: {summary.get('duration_days', 0)} days")
                output.append(f"Estimated Budget: ${summary.get('total_budget', 0):.2f}")
                output.append("")
            except Exception as e:
                print(f"Error formatting trip summary: {str(e)}")
                output.append("Trip Summary: Error formatting this section")
        
        # Add daily itinerary
        if "daily_itinerary" in itinerary_data:
            try:
                output.append("📅 DAILY ITINERARY")
                output.append("=" * 80)
                
                for day_key, day_data in sorted(itinerary_data["daily_itinerary"].items()):
                    try:
                        output.append(f"\n📆 {day_data.get('date', 'Unknown')} - {day_key.replace('_', ' ').title()}")
                        output.append("-" * 80)
                        
                        if "activities" in day_data:
                            for activity in day_data["activities"]:
                                try:
                                    # Format activity title and time
                                    title = activity.get('title', 'Unknown Activity')
                                    time = activity.get('time', '')
                                    if time:
                                        output.append(f"\n🕒 {time} - {title}")
                                    else:
                                        output.append(f"\n• {title}")
                                    
                                    # Add details if available
                                    if "details" in activity:
                                        details = activity["details"]
                                        
                                        if "name" in details:
                                            output.append(f"  📍 {details['name']}")
                                        
                                        if "location" in details:
                                            output.append(f"  📍 {details['location']}")
                                        
                                        if "price" in details:
                                            try:
                                                output.append(f"  💰 ${details['price']:.2f}")
                                            except (ValueError, TypeError):
                                                output.append(f"  💰 ${details['price']}")
                                        
                                        if "description" in details and details["description"]:
                                            output.append(f"  ℹ️ {details['description']}")
                                    
                                    # Add review insights if available
                                    if "review_insights" in activity:
                                        insights = activity["review_insights"]
                                        
                                        if "summary" in insights and insights["summary"]:
                                            output.append(f"  💬 {insights['summary']}")
                                        
                                        if "strengths" in insights and insights["strengths"]:
                                            strengths = insights["strengths"]
                                            if isinstance(strengths, list) and strengths:
                                                output.append(f"  ✅ {strengths[0]}")
                                        
                                        if "weaknesses" in insights and insights["weaknesses"]:
                                            weaknesses = insights["weaknesses"]
                                            if isinstance(weaknesses, list) and weaknesses:
                                                output.append(f"  ⚠️ {weaknesses[0]}")
                                except Exception as e:
                                    print(f"Error formatting activity: {str(e)}")
                                    output.append(f"\n• Activity (formatting error)")
                        
                        output.append("")
                    except Exception as e:
                        print(f"Error formatting day {day_key}: {str(e)}")
                        output.append(f"\n📆 {day_key} - Error formatting this day")
                        output.append("")
            except Exception as e:
                print(f"Error formatting daily itinerary: {str(e)}")
                output.append("Daily Itinerary: Error formatting this section")
        
        # Add review highlights
        if "review_highlights" in itinerary_data:
            try:
                highlights = itinerary_data["review_highlights"]
                
                if "top_rated_places" in highlights and highlights["top_rated_places"]:
                    try:
                        output.append("\n🏆 TOP RATED ATTRACTIONS")
                        output.append("-" * 80)
                        for place in highlights["top_rated_places"]:
                            output.append(f"• {place.get('name', 'Unknown')}")
                            if "rating" in place:
                                output.append(f"  ⭐ {place.get('rating', 0)}/5")
                            if "summary" in place and place["summary"]:
                                output.append(f"  💬 {place['summary']}")
                            output.append("")
                    except Exception as e:
                        print(f"Error formatting top places: {str(e)}")
                        output.append("Top Places: Error formatting this section")
                
                if "top_rated_restaurants" in highlights and highlights["top_rated_restaurants"]:
                    try:
                        output.append("\n🍽️ TOP RATED RESTAURANTS")
                        output.append("-" * 80)
                        for restaurant in highlights["top_rated_restaurants"]:
                            output.append(f"• {restaurant.get('name', 'Unknown')}")
                            if "rating" in restaurant:
                                output.append(f"  ⭐ {restaurant.get('rating', 0)}/5")
                            if "summary" in restaurant and restaurant["summary"]:
                                output.append(f"  💬 {restaurant['summary']}")
                            output.append("")
                    except Exception as e:
                        print(f"Error formatting top restaurants: {str(e)}")
                        output.append("Top Restaurants: Error formatting this section")
                
                if "hotel_review_summary" in highlights:
                    try:
                        hotel = highlights["hotel_review_summary"]
                        output.append("\n🏨 ACCOMMODATION REVIEW")
                        output.append("-" * 80)
                        output.append(f"• {hotel.get('name', 'Your Hotel')}")
                        if "rating" in hotel:
                            output.append(f"  ⭐ {hotel.get('rating', 0)}/5")
                        if "summary" in hotel and hotel["summary"]:
                            output.append(f"  💬 {hotel['summary']}")
                        output.append("")
                    except Exception as e:
                        print(f"Error formatting hotel review: {str(e)}")
                        output.append("Hotel Review: Error formatting this section")
            except Exception as e:
                print(f"Error formatting review highlights: {str(e)}")
                output.append("Review Highlights: Error formatting this section")
        
        return "\n".join(output)
        
    except Exception as e:
        import traceback
        print(f"Error in generate_readable_itinerary: {str(e)}")
        print(traceback.format_exc())
        return f"There was an error formatting your itinerary. Raw data:\n\n{str(itinerary_data)[:1000]}..."

async def add_coordinates_to_itinerary(itinerary_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add latitude and longitude coordinates to places in the itinerary.
    
    Args:
        itinerary_data: The generated itinerary
        
    Returns:
        Updated itinerary with coordinates
    """
    if not isinstance(itinerary_data, dict):
        return itinerary_data
    
    try:
        # Initialize the LocationCoordinates class
        location_service = LocationCoordinates()
        
        # Collect all unique places to get coordinates for
        places_to_geocode = set()
        
        # Extract places from daily itinerary
        if "daily_itinerary" in itinerary_data:
            for day_key, day_data in itinerary_data["daily_itinerary"].items():
                if "activities" in day_data:
                    for activity in day_data["activities"]:
                        if "details" in activity:
                            # For attractions and dining, we need coordinates
                            if activity["type"] in ["attraction", "dining", "accommodation"]:
                                # Try to get location from different fields
                                location = None
                                if "location" in activity["details"]:
                                    location = activity["details"]["location"]
                                elif "name" in activity["details"]:
                                    location = activity["details"]["name"]
                                
                                if location:
                                    places_to_geocode.add(location)
        
        print(f"Places to geocode: {places_to_geocode}")
        
        # Get coordinates for all places
        coordinates_cache = {}
        for place_name in places_to_geocode:
            print(f"Getting coordinates for: {place_name}")
            coords = await location_service.get_coordinates(place_name)
            if coords:
                print(f"Found coordinates for {place_name}: {coords}")
                coordinates_cache[place_name] = coords
            else:
                print(f"Failed to get coordinates for: {place_name}")
        
        # Add coordinates to activities
        if "daily_itinerary" in itinerary_data:
            for day_key, day_data in itinerary_data["daily_itinerary"].items():
                if "activities" in day_data:
                    for activity in day_data["activities"]:
                        if "details" in activity:
                            # Check for location or name match
                            matched_place = None
                            
                            if "location" in activity["details"] and activity["details"]["location"] in coordinates_cache:
                                matched_place = activity["details"]["location"]
                            elif "name" in activity["details"] and activity["details"]["name"] in coordinates_cache:
                                matched_place = activity["details"]["name"]
                            
                            if matched_place:
                                coords = coordinates_cache[matched_place]
                                # Add coordinates directly to details
                                activity["details"]["latitude"] = coords["lat"]
                                activity["details"]["longitude"] = coords["lon"]
                                print(f"Added coordinates to {matched_place}: Lat={coords['lat']}, Lon={coords['lon']}")
        
        return itinerary_data
        
    except Exception as e:
        import traceback
        print(f"Error adding coordinates to itinerary: {str(e)}")
        print(traceback.format_exc())
        return itinerary_data

async def summary_node(state: GraphState) -> GraphState:
    """
    Generate a detailed itinerary based on all the collected information.
    
    Args:
        state: Current state containing all trip information
        
    Returns:
        Updated state with generated itinerary
    """
    # Check if we have metadata for required information
    if "metadata" not in state or not state["metadata"]:
        state["error"] = "No trip metadata available for summary"
        state["itinerary"] = "No itinerary could be generated."
        return state
    
    # Use selected flights if available, otherwise use all flights
    flights_to_use = state.get("selected_flights", []) or state.get("flights", [])
    
    try:
        # Debug logging
        print("=== DEBUG INFO ===")
        print(f"Metadata: {state.get('metadata', None) is not None}")
        print(f"Flights: {len(flights_to_use)} available")
        print(f"Hotel data: {bool(state.get('hotel', {}))}")
        print(f"Places data: {len(state.get('places', []))}")
        print(f"Restaurants data: {len(state.get('restaurants', []))}")
        print("=================")
        
        # Prepare data for the prompt
        try:
            # Extract and prepare metadata (handle potential circular references)
            metadata = state.get("metadata")
            if metadata is not None:
                if hasattr(metadata, 'dict'):
                    try:
                        metadata_dict = metadata.dict()
                    except Exception:
                        if hasattr(metadata, 'model_dump'):
                            metadata_dict = metadata.model_dump()
                        else:
                            metadata_dict = {
                                "source": getattr(metadata, "source", "Unknown"),
                                "destination": getattr(metadata, "destination", "Unknown"),
                                "start_date": getattr(metadata, "start_date", None),
                                "end_date": getattr(metadata, "end_date", None),
                                "num_people": getattr(metadata, "num_people", 1),
                                "preferences": getattr(metadata, "preferences", [])
                            }
                else:
                    metadata_dict = metadata
            else:
                metadata_dict = {}
                
            # Use safe_json_dumps to handle circular references
            metadata_json = safe_json_dumps(metadata_dict, indent=2)
            flights_json = safe_json_dumps(flights_to_use, indent=2)
            hotel_json = safe_json_dumps(state.get("hotel", {}), indent=2)
            places_json = safe_json_dumps(state.get("places", []), indent=2)
            restaurants_json = safe_json_dumps(state.get("restaurants", []), indent=2)
            budget_json = safe_json_dumps(state.get("budget", {}), indent=2)
            route_json = safe_json_dumps(state.get("route", {}), indent=2)
            print("Successfully serialized all data to JSON")
        except Exception as e:
            print(f"Error serializing data to JSON: {str(e)}")
            state["error"] = f"Error preparing data: {str(e)}"
            state["itinerary"] = "Error preparing itinerary data. Please try again."
            return state
        
        # Format the prompt
        try:
            prompt = ITINERARY_PROMPT.format(
                metadata=metadata_json,
                selected_flights=flights_json,
                hotel=hotel_json,
                places=places_json,
                restaurants=restaurants_json,
                budget=budget_json,
                route=route_json
            )
            print("Successfully formatted prompt template")
        except Exception as e:
            print(f"Error formatting prompt: {str(e)}")
            state["error"] = f"Error formatting prompt: {str(e)}"
            state["itinerary"] = "Error preparing itinerary prompt. Please try again."
            return state
        
        # Initialize LLM
        try:
            llm = ChatAnthropic(
                model="claude-3-sonnet-20240229",
                temperature=0.3,
                max_tokens=4000
            )
            print("Successfully initialized LLM")
        except Exception as e:
            print(f"Error initializing LLM: {str(e)}")
            state["error"] = f"Error initializing language model: {str(e)}"
            state["itinerary"] = "Error with language model. Please try again."
            return state
        
        # Get the itinerary from Claude
        try:
            print("Calling Claude API...")
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            print("Successfully received response from Claude")
        except Exception as e:
            print(f"Error calling Claude API: {str(e)}")
            state["error"] = f"Error generating content: {str(e)}"
            state["itinerary"] = "Error communicating with language model. Please try again."
            return state
        
        # Parse the response content
        try:
            # Handle any markdown code blocks in the response
            content = response.content
            print(f"Raw content length: {len(content)}")
            print(f"Content preview: {content[:200]}...")
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
                print("Extracted JSON from code block with 'json' tag")
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                print("Extracted JSON from generic code block")
            
            # Parse the JSON
            print("Attempting to parse JSON...")
            itinerary_data = json.loads(content)
            print("Successfully parsed JSON")
            
            # Merge review insights
            print("Merging review insights...")
            itinerary_data = merge_review_insights(itinerary_data, state)
            print("Successfully merged review insights")
            
            # Add coordinates to places in the itinerary
            print("Adding coordinates to places in the itinerary...")
            itinerary_data = await add_coordinates_to_itinerary(itinerary_data)
            print("Successfully added coordinates")
            
            # Print full JSON result
            print("\nComplete itinerary JSON:")
            print(json.dumps(itinerary_data, indent=2, default=datetime_to_str))
            
            # Ask user if they want to modify the itinerary
            print("\n" + "-" * 80)
            user_response = input("Would you like to modify any aspect of this itinerary? (y/n): ")
            if user_response.lower() != 'y':
                print("\nFull itinerary JSON with latitude and longitude:")
                print(json.dumps(itinerary_data, indent=2, default=datetime_to_str))
                
                # Print a summary of coordinates added
                print("\nLocation Coordinates Summary:")
                print("-" * 40)
                for day_key, day_data in itinerary_data["daily_itinerary"].items():
                    if "activities" in day_data:
                        for activity in day_data["activities"]:
                            if "details" in activity:
                                details = activity["details"]
                                name = details.get("name", "")
                                location = details.get("location", "")
                                lat = details.get("latitude")
                                lon = details.get("longitude")
                                
                                if lat and lon:
                                    place = name or location
                                    print(f"{place}: Latitude={lat}, Longitude={lon}")
            
            # Add JSON directly to state instead of converting to readable format
            state["itinerary"] = itinerary_data
            print("Added itinerary JSON to state")
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {str(e)}")
            print(f"Problematic content: {content[:500]}...")
            state["error"] = f"Failed to parse itinerary JSON: {str(e)}"
            
            # Try to extract any text content that might be useful
            cleaned_content = content.replace("```json", "").replace("```", "").strip()
            state["itinerary"] = f"We couldn't format your itinerary properly, but here's what we have:\n\n{cleaned_content[:2000]}..."
            
            return state
        except Exception as e:
            print(f"Error in response processing: {str(e)}")
            state["error"] = f"Failed to process itinerary: {str(e)}"
            state["itinerary"] = response.content if hasattr(response, 'content') else "Response processing failed. Please try again."
            return state
        
        return state
        
    except Exception as e:
        import traceback
        print(f"Unexpected error in summary_node: {str(e)}")
        print(traceback.format_exc())
        state["error"] = f"Error generating itinerary: {str(e)}"
        state["itinerary"] = "An error occurred while generating your itinerary."
        return state 