import asyncio
from app.graph.trip_planner_graph import TripPlannerGraph
from app.utils.logger import logger

async def test_trip_planner():
    """Test the trip planner with a simple travel query."""
    print("\n=== Testing Trip Planner ===")
    
    # Create graph instance
    graph = TripPlannerGraph()
    
    # Test query with more specific details
    query = "I want to plan a 3-day trip to Paris for 2 people from May 20, 2024 to May 22, 2024. We're interested in museums, historical sites, and local cuisine. Budget is around $2000 per person."
    print(f"\nTest Query: {query}")
    
    # Initialize state with all required fields
    state = {
        "query": query,
        "raw_query": query,
        "metadata": {
            "destination": "Paris, France",
            "start_date": "2024-05-20",
            "end_date": "2024-05-22",
            "duration": 3,
            "travelers": 2,
            "budget_per_person": 2000,
            "preferences": ["museums", "historical sites", "local cuisine"]
        },
        "is_valid": False,
        "next_question": None,
        "error": None,
        "thought": None,
        "action": None,
        "action_input": None,
        "observation": None,
        "current_day": 1,
        "total_days": 3,
        "nodes_to_call": [],
        "flights": [],
        "places": [],
        "restaurants": [],
        "hotel": {},
        "budget": {},
        "route": {},
        "daily_itineraries": [],
        "visited_places": set(),
        "visited_restaurants": set(),
        "final_itinerary": None
    }
    
    try:
        # Process the query
        print("\nProcessing query...")
        result = await graph.process(state)
        
        # Print results
        print("\nResults:")
        print("-" * 50)
        print(f"Valid: {result.get('is_valid', False)}")
        
        if result.get('error'):
            print(f"Error: {result['error']}")
        
        if result.get('next_question'):
            print(f"Next Question: {result['next_question']}")
        
        if result.get('metadata'):
            print("\nExtracted Metadata:")
            metadata = result['metadata']
            if isinstance(metadata, dict):
                for key, value in metadata.items():
                    print(f"- {key}: {value}")
            else:
                # Handle TripMetadata object
                metadata_dict = metadata.dict()
                for key, value in metadata_dict.items():
                    print(f"- {key}: {value}")
        
        # Print daily itineraries
        if result.get('daily_itineraries'):
            print("\nDaily Itineraries:")
            for i, day in enumerate(result['daily_itineraries'], 1):
                print(f"\nDay {i}:")
                print("-" * 30)
                for activity in day.get('activities', []):
                    print(f"- {activity.get('time')}: {activity.get('name')}")
                    print(f"  Duration: {activity.get('duration')}")
                    print(f"  Location: {activity.get('location')}")
                print(f"Total cost for day: ${day.get('total_cost', 0)}")
        
        # Print final itinerary summary
        if result.get('final_itinerary'):
            print("\nFinal Itinerary Summary:")
            print("-" * 50)
            print(f"Total Days: {result['final_itinerary'].get('total_days')}")
            print(f"Total Cost: ${result['final_itinerary'].get('total_cost')}")
            print(f"Unique Places Visited: {result['final_itinerary'].get('unique_places_visited')}")
            print(f"Unique Restaurants Visited: {result['final_itinerary'].get('unique_restaurants_visited')}")
        
        # Print visited places tracking
        if result.get('visited_places'):
            print("\nVisited Places:")
            for place in result['visited_places']:
                print(f"- {place}")
        
        if result.get('visited_restaurants'):
            print("\nVisited Restaurants:")
            for restaurant in result['visited_restaurants']:
                print(f"- {restaurant}")
        
        print("-" * 50)
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        print(f"\nError occurred: {str(e)}")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_trip_planner()) 