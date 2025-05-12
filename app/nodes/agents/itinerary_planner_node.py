from typing import Dict, Any, List, Optional, TypedDict
from langchain_anthropic import ChatAnthropic
from app.schemas.trip_schema import TripMetadata

ITINERARY_PLANNER_PROMPT = """You are a daily itinerary planner. Create a detailed schedule for day {current_day} of a {total_days}-day trip.

Available information:
- Flights: {flights}
- Places to visit: {places}
- Restaurant options: {restaurants}
- Hotel: {hotel}
- Budget constraints: {budget}
- Route information: {route}

Previous days' activities:
{previous_days}

Create a schedule that:
1. Respects opening hours and travel times
2. Groups nearby activities together
3. Includes meals at appropriate times
4. Stays within budget
5. Avoids revisiting places from previous days

Return the schedule as a JSON object with:
- activities: list of activities with time, duration, location, and cost
- total_cost: total cost for the day
- notes: any important notes about the schedule

Format:
{
    "activities": [
        {
            "time": "HH:MM",
            "name": "Activity name",
            "duration": "X hours",
            "location": "Location name",
            "cost": cost_in_dollars
        }
    ],
    "total_cost": total_cost,
    "notes": "Important notes"
}
"""

class GraphState(TypedDict):
    """State for the LangGraph pipeline."""
    current_day: int
    total_days: int
    flights: List[Dict[str, Any]]
    places: List[Dict[str, Any]]
    restaurants: List[Dict[str, Any]]
    hotel: Dict[str, Any]
    budget: Dict[str, Any]
    route: Dict[str, Any]
    daily_itineraries: List[Dict[str, Any]]
    visited_places: set
    visited_restaurants: set

async def itinerary_planner_node(state: GraphState) -> GraphState:
    """
    Create a daily itinerary based on available options and constraints.
    
    Args:
        state: Current state containing all necessary information
        
    Returns:
        Updated state with the new daily itinerary
    """
    try:
        # Initialize LLM
        llm = ChatAnthropic(
            model="claude-3-haiku-20240307",
            temperature=0.2,
            max_tokens=1000
        )
        
        # Get previous days' activities
        previous_days = state.get('daily_itineraries', [])
        
        # Use Claude to create the daily schedule
        response = await llm.ainvoke(
            ITINERARY_PLANNER_PROMPT.format(
                current_day=state.get('current_day', 1),
                total_days=state.get('total_days', 1),
                flights=state.get('flights', []),
                places=state.get('places', []),
                restaurants=state.get('restaurants', []),
                hotel=state.get('hotel', {}),
                budget=state.get('budget', {}),
                route=state.get('route', {}),
                previous_days=previous_days
            )
        )
        
        # Parse the response
        import json
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        daily_itinerary = json.loads(content)
        
        # Update visited places and restaurants
        for activity in daily_itinerary.get('activities', []):
            if activity.get('location') in state.get('places', []):
                state['visited_places'].add(activity['location'])
            if activity.get('location') in state.get('restaurants', []):
                state['visited_restaurants'].add(activity['location'])
        
        # Add to daily itineraries
        state['daily_itineraries'].append(daily_itinerary)
        
        # Increment current day
        state['current_day'] += 1
        
        return state
        
    except Exception as e:
        state['error'] = f"Failed to create daily itinerary: {str(e)}"
        return state 