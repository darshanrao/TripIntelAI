import asyncio
from app.graph.trip_planner_graph import TripPlannerGraph
from app.utils.logger import logger

async def verify_agent_data(agent_name: str, data: any) -> bool:
    """Verify the data returned by an agent."""
    if not data:
        return False
    
    if isinstance(data, list):
        return len(data) > 0
    elif isinstance(data, dict):
        return len(data.keys()) > 0
    elif isinstance(data, set):
        return len(data) > 0
    return True

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
        "is_valid": True,  # Set to True since we're providing complete metadata
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
        
        # Verify planner node execution
        print("\nVerifying Planner Node:")
        print("-" * 50)
        if result.get('nodes_to_call'):
            print("Planner node successfully called and returned nodes to call:")
            for node in result['nodes_to_call']:
                print(f"- {node}")
            
            # Verify that all necessary nodes are called
            expected_nodes = {'flights', 'places', 'hotel', 'budget'}
            called_nodes = set(result['nodes_to_call'])
            missing_nodes = expected_nodes - called_nodes
            if missing_nodes:
                print(f"\nWarning: Missing expected nodes: {missing_nodes}")
            else:
                print("\nAll expected nodes are included in the plan")
        else:
            print("Warning: Planner node did not return any nodes to call")
        
        # Verify specialized agents execution
        print("\nVerifying Specialized Agents:")
        print("-" * 50)
        
        # Check flights agent
        if result.get('flights'):
            print("\nFlights agent executed successfully")
            print(f"Found {len(result['flights'])} flight options")
            # Verify flight data structure
            if len(result['flights']) > 0:
                flight = result['flights'][0]
                required_fields = {'airline', 'flight_number', 'departure_airport', 'arrival_airport', 'price'}
                missing_fields = required_fields - set(flight.keys())
                if missing_fields:
                    print(f"Warning: Flight data missing required fields: {missing_fields}")
                else:
                    print("Flight data structure is valid")
        else:
            print("\nWarning: Flights agent did not return any results")
        
        # Check places agent
        if result.get('places'):
            print("\nPlaces agent executed successfully")
            print(f"Found {len(result['places'])} places to visit")
            # Verify places data structure
            if len(result['places']) > 0:
                place = result['places'][0]
                required_fields = {'name', 'location', 'type', 'rating'}
                missing_fields = required_fields - set(place.keys())
                if missing_fields:
                    print(f"Warning: Place data missing required fields: {missing_fields}")
                else:
                    print("Place data structure is valid")
        else:
            print("\nWarning: Places agent did not return any results")
        
        # Check restaurants
        if result.get('restaurants'):
            print("\nRestaurants agent executed successfully")
            print(f"Found {len(result['restaurants'])} restaurants")
            # Verify restaurant data structure
            if len(result['restaurants']) > 0:
                restaurant = result['restaurants'][0]
                required_fields = {'name', 'cuisine', 'price_range', 'rating'}
                missing_fields = required_fields - set(restaurant.keys())
                if missing_fields:
                    print(f"Warning: Restaurant data missing required fields: {missing_fields}")
                else:
                    print("Restaurant data structure is valid")
        else:
            print("\nWarning: Restaurants agent did not return any results")
        
        # Check hotel
        if result.get('hotel'):
            print("\nHotel agent executed successfully")
            print("Hotel information found")
            # Verify hotel data structure
            required_fields = {'name', 'location', 'price_per_night', 'rating', 'amenities'}
            missing_fields = required_fields - set(result['hotel'].keys())
            if missing_fields:
                print(f"Warning: Hotel data missing required fields: {missing_fields}")
            else:
                print("Hotel data structure is valid")
        else:
            print("\nWarning: Hotel agent did not return any results")
        
        # Check budget
        if result.get('budget'):
            print("\nBudget agent executed successfully")
            print("Budget information found")
            # Verify budget data structure
            required_fields = {'total_budget', 'flights_cost', 'accommodation_cost', 'activities_cost', 'food_cost'}
            missing_fields = required_fields - set(result['budget'].keys())
            if missing_fields:
                print(f"Warning: Budget data missing required fields: {missing_fields}")
            else:
                print("Budget data structure is valid")
        else:
            print("\nWarning: Budget agent did not return any results")
        
        # Check route
        if result.get('route'):
            print("\nRoute agent executed successfully")
            print("Route information found")
            # Verify route data structure
            required_fields = {'total_distance', 'estimated_time', 'waypoints'}
            missing_fields = required_fields - set(result['route'].keys())
            if missing_fields:
                print(f"Warning: Route data missing required fields: {missing_fields}")
            else:
                print("Route data structure is valid")
        else:
            print("\nWarning: Route agent did not return any results")
        
        # Verify data consistency
        print("\nVerifying Data Consistency:")
        print("-" * 50)
        
        # Check if visited places match places in itineraries
        if result.get('visited_places') and result.get('daily_itineraries'):
            itinerary_places = set()
            for day in result['daily_itineraries']:
                for activity in day.get('activities', []):
                    if 'location' in activity:
                        itinerary_places.add(activity['location'])
            
            missing_places = itinerary_places - result['visited_places']
            if missing_places:
                print(f"Warning: Places in itineraries not tracked in visited_places: {missing_places}")
            else:
                print("Visited places tracking is consistent with itineraries")
        
        # Check if daily itineraries match total days
        if result.get('daily_itineraries'):
            if len(result['daily_itineraries']) != result.get('total_days', 0):
                print(f"Warning: Number of daily itineraries ({len(result['daily_itineraries'])}) doesn't match total days ({result.get('total_days', 0)})")
            else:
                print("Daily itineraries match total days")
        
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