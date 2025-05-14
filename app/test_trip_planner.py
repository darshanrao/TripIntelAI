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
        "nodes_to_call": [],
        "flights": [],
        "places": [],
        "restaurants": [],
        "hotel": {},
        "budget": {},
        "route": {}
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
                required_fields = {
                    'id', 'airline', 'flight_number', 'departure_airport', 
                    'departure_city', 'arrival_airport', 'arrival_city',
                    'departure_time', 'arrival_time', 'price'
                }
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
            required_fields = {'total', 'accommodation', 'food', 'activities', 'transportation'}
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
        if result.get('visited_places') and result.get('final_itinerary'):
            itinerary_places = set()
            for day_key, day_data in result['final_itinerary'].get('daily_itinerary', {}).items():
                for activity in day_data.get('activities', []):
                    if activity.get('type') == 'attraction':
                        itinerary_places.add(activity.get('title', ''))
            
            missing_places = itinerary_places - result['visited_places']
            if missing_places:
                print(f"Warning: Places in itineraries not tracked in visited_places: {missing_places}")
            else:
                print("Visited places tracking is consistent with itineraries")
        
        # Check if daily itineraries match total days
        if result.get('final_itinerary') and result.get('final_itinerary').get('daily_itinerary'):
            daily_itinerary = result['final_itinerary']['daily_itinerary']
            if len(daily_itinerary) != result.get('total_days', 0):
                print(f"Warning: Number of daily itineraries ({len(daily_itinerary)}) doesn't match total days ({result.get('total_days', 0)})")
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
        
        # Print final itinerary
        if result.get('final_itinerary'):
            print("\nFinal Itinerary:")
            final_itinerary = result['final_itinerary']
            
            # Print trip summary
            print("\nTrip Summary:")
            print("-" * 30)
            trip_summary = final_itinerary.get('trip_summary', {})
            print(f"Destination: {trip_summary.get('destination', 'Unknown')}")
            print(f"Start Date: {trip_summary.get('start_date', 'Unknown')}")
            print(f"End Date: {trip_summary.get('end_date', 'Unknown')}")
            print(f"Duration: {trip_summary.get('duration_days', 0)} days")
            print(f"Total Budget: ${trip_summary.get('total_budget', 0)}")
            
            # Print daily itineraries
            daily_itinerary = final_itinerary.get('daily_itinerary', {})
            for day_num in range(1, result.get('total_days', 0) + 1):
                day_key = f"day_{day_num}"
                if day_key in daily_itinerary:
                    day_data = daily_itinerary[day_key]
                    print(f"\nDay {day_num} ({day_data.get('date', 'Unknown')}):")
                    print("-" * 30)
                    
                    for activity in day_data.get('activities', []):
                        print(f"- {activity.get('time')}: {activity.get('title')}")
                        print(f"  Type: {activity.get('type')}")
                        print(f"  Category: {activity.get('category')}")
                        print(f"  Duration: {activity.get('duration_minutes')} minutes")
            
            # Print review highlights
            review_highlights = final_itinerary.get('review_highlights', {})
            if review_highlights:
                print("\nReview Highlights:")
                print("-" * 30)
                
                if review_highlights.get('hotel_review_summary'):
                    hotel_review = review_highlights['hotel_review_summary']
                    print(f"Hotel: {hotel_review.get('name', 'Unknown')} - Rating: {hotel_review.get('rating', 0)}")
                
                if review_highlights.get('overall'):
                    print("\nOverall Highlights:")
                    for highlight in review_highlights.get('overall', []):
                        print(f"- {highlight}")
                
                if review_highlights.get('attractions'):
                    print("\nAttraction Highlights:")
                    for highlight in review_highlights.get('attractions', []):
                        print(f"- {highlight}")
                
                if review_highlights.get('dining'):
                    print("\nDining Highlights:")
                    for highlight in review_highlights.get('dining', []):
                        print(f"- {highlight}")
        
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
        
        # Save results to JSON file
        try:
            import json
            from datetime import datetime
            import re
            from pathlib import Path
            
            # Custom JSON encoder to handle various object types
            class EnhancedJSONEncoder(json.JSONEncoder):
                def default(self, obj):
                    # Handle datetime objects
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    
                    # Handle Pydantic models
                    if hasattr(obj, 'dict'):
                        return obj.dict()
                    
                    # Handle sets
                    if isinstance(obj, set):
                        return list(obj)
                    
                    # Handle any other non-serializable objects
                    try:
                        return str(obj)
                    except:
                        return None
            
            # Create safe filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = re.sub(r'[^\w\-_.]', '_', f"itinerary_{timestamp}.json")
            
            # Ensure we're saving in a safe directory
            output_dir = Path("results")
            output_dir.mkdir(exist_ok=True)
            filepath = output_dir / safe_filename
            
            # Get the final itinerary
            final_itinerary = result.get('final_itinerary', {})
            
            # Add location details to activities
            if 'daily_itinerary' in final_itinerary:
                for day_key, day_data in final_itinerary['daily_itinerary'].items():
                    for activity in day_data.get('activities', []):
                        # Initialize details if not present
                        if 'details' not in activity:
                            activity['details'] = {}
                        
                        # Find matching place or restaurant
                        if activity['type'] in ['attraction', 'dining']:
                            # Search in places
                            if activity['type'] == 'attraction':
                                for place in result.get('places', []):
                                    if place.get('name') == activity['title']:
                                        activity['details'].update({
                                            'location': place.get('location', ''),
                                            'latitude': place.get('latitude'),
                                            'longitude': place.get('longitude')
                                        })
                                        break
                            # Search in restaurants
                            elif activity['type'] == 'dining':
                                for restaurant in result.get('restaurants', []):
                                    if restaurant.get('name') == activity['title']:
                                        activity['details'].update({
                                            'location': restaurant.get('location', ''),
                                            'latitude': restaurant.get('latitude'),
                                            'longitude': restaurant.get('longitude')
                                        })
                                        break
            
            # Validate JSON before saving
            try:
                # First try to serialize to JSON string to validate
                json_str = json.dumps(final_itinerary, cls=EnhancedJSONEncoder, ensure_ascii=False)
                # Then parse it back to ensure it's valid
                json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"\nWarning: Invalid JSON data detected: {str(e)}")
                # Try to clean the data
                if 'daily_itinerary' in final_itinerary:
                    for day_key, day_data in final_itinerary['daily_itinerary'].items():
                        if 'activities' in day_data:
                            # Remove any invalid activities
                            day_data['activities'] = [
                                activity for activity in day_data['activities']
                                if isinstance(activity, dict) and 'title' in activity
                            ]
            
            # Save only the final itinerary to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(final_itinerary, f, indent=2, cls=EnhancedJSONEncoder, ensure_ascii=False)
            print(f"\nItinerary saved to {filepath}")
            
        except Exception as e:
            print(f"\nWarning: Failed to save itinerary to JSON file: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return result
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        print(f"\nError occurred: {str(e)}")
        raise

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_trip_planner()) 