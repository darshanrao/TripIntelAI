import asyncio
import json
import os
from dotenv import load_dotenv
from mock_trip_data import create_mock_trip_data
from app.nodes.agents.itinerary_planner_node import itinerary_planner_node
from app.utils.logger import logger

# Load environment variables
load_dotenv()

async def generate_mock_itinerary():
    """
    Generate a complete itinerary using the itinerary planner node and mock data.
    """
    print("\n=== Generating Mock Itinerary ===")
    
    # Get mock trip data
    trip_data = create_mock_trip_data()
    
    # Initialize the graph state
    state = {
        "current_day": 1,
        "total_days": trip_data["total_days"],
        "destination": trip_data["destination"],
        "start_date": trip_data["start_date"],
        "flights": trip_data["flights"],
        "places": trip_data["places"],
        "restaurants": trip_data["restaurants"],
        "hotel": trip_data["hotel"],
        "budget": trip_data["budget"],
        "route": {},
        "daily_itineraries": [],
        "visited_places": set(),
        "visited_restaurants": set(),
        "final_itinerary": None
    }
    
    try:
        # Generate itinerary for each day
        for day in range(1, trip_data["total_days"] + 1):
            print(f"\n\n=== Planning Day {day} ===")
            
            # Call the itinerary planner node
            state = await itinerary_planner_node(state)
            
            # Check for errors
            if "error" in state:
                print(f"Error: {state['error']}")
                return None
            
            # Print the day's itinerary
            day_itinerary = state["final_itinerary"]["daily_itinerary"].get(f"day_{day}")
            if day_itinerary:
                print(f"\nDay {day} Itinerary:")
                print("-" * 50)
                print(f"Date: {day_itinerary.get('date')}")
                for activity in day_itinerary.get('activities', []):
                    print(f"- {activity.get('time')}: {activity.get('title')}")
                    print(f"  Type: {activity.get('type')}")
                    print(f"  Category: {activity.get('category')}")
                    print(f"  Duration: {activity.get('duration_minutes')} minutes")
            
        # Print summary
        final_itinerary = state["final_itinerary"]
        print("\n\n=== Trip Summary ===")
        print("-" * 50)
        print(f"Destination: {final_itinerary['trip_summary']['destination']}")
        print(f"Start Date: {final_itinerary['trip_summary']['start_date']}")
        print(f"End Date: {final_itinerary['trip_summary']['end_date'] or 'Not set'}")
        print(f"Total Days: {final_itinerary['trip_summary']['duration_days']}")
        
        # Save the final itinerary to a file
        with open("mock_itinerary_output.json", "w") as f:
            json.dump(final_itinerary, f, indent=2)
        print("\nFinal itinerary saved to mock_itinerary_output.json")
        
        return final_itinerary
        
    except Exception as e:
        logger.error(f"Error generating itinerary: {str(e)}")
        print(f"\nError occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Run the generator
    asyncio.run(generate_mock_itinerary()) 