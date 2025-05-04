import asyncio
import os
from dotenv import load_dotenv
from app.graph.trip_planner_graph_mock import TripPlannerGraphMock

# Load environment variables
load_dotenv()

async def test_mock_graph():
    # Initialize the graph
    trip_planner = TripPlannerGraphMock()
    
    # Test query
    query = "I want to plan a trip from Boston to NYC from May 15 to May 18, 2025 for 2 people with focus on museums and good restaurants"
    
    print(f"Processing query: {query}")
    try:
        # Process the query
        result = await trip_planner.process(query)
        
        # Check if validation passed
        if not result.get("is_valid", True):
            print("Trip validation failed:")
            for error in result.get("validation_errors", []):
                print(f"- {error}")
            return
        
        # Print the generated itinerary
        print("\nGENERATED ITINERARY:")
        print("=" * 80)
        print(result.get("itinerary", "No itinerary generated"))
        print("=" * 80)
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_mock_graph()) 