import asyncio
import os
from dotenv import load_dotenv
from pprint import pprint
from app.nodes.chat_input_node import chat_input_node
from mock_intent_parser import mock_intent_parser  # Use mock parser instead
from app.nodes.trip_validator_node import trip_validator_node
from app.nodes.planner_node import planner_node
from app.nodes.agent_nodes import flights_node, places_node, restaurants_node, hotel_node, budget_node, reviews_node
from app.nodes.summary_node import summary_node

# Load environment variables
load_dotenv()

async def test_pipeline_step_by_step():
    """Test each node in the pipeline sequentially"""
    # Test query
    query = "I want to plan a trip from Boston to NYC from May 15 to May 18, 2025 for 2 people with focus on museums and good restaurants"
    
    print(f"Processing query: {query}")
    
    try:
        # Initial state
        state = {"query": query}
        
        # Step 1: Chat Input Node
        print("\n=== STEP 1: Chat Input Node ===")
        state = await chat_input_node(state)
        print("Raw query extracted:")
        pprint(state)
        
        # Step 2: Intent Parser Node (using mock)
        print("\n=== STEP 2: Mock Intent Parser Node ===")
        state = await mock_intent_parser(state)
        print("Metadata extracted:")
        if "metadata" in state and state["metadata"]:
            print(f"Source: {state['metadata'].source}")
            print(f"Destination: {state['metadata'].destination}")
            print(f"Start date: {state['metadata'].start_date}")
            print(f"End date: {state['metadata'].end_date}")
            print(f"Number of people: {state['metadata'].num_people}")
            print(f"Preferences: {state['metadata'].preferences}")
        else:
            print("No metadata extracted")
            print(f"Error: {state.get('error')}")
            return
        
        # Step 3: Trip Validator Node
        print("\n=== STEP 3: Trip Validator Node ===")
        state = await trip_validator_node(state)
        print(f"Is valid: {state.get('is_valid', False)}")
        if not state.get('is_valid', False):
            print("Validation errors:")
            for error in state.get('validation_errors', []):
                print(f"- {error}")
            return
        
        # Step 4: Planner Node
        print("\n=== STEP 4: Planner Node ===")
        state = await planner_node(state)
        print(f"Nodes to call: {state.get('nodes_to_call', [])}")
        
        # Step 5: Agent Nodes
        nodes_to_call = state.get('nodes_to_call', [])
        
        if 'flights' in nodes_to_call:
            print("\n=== STEP 5a: Flights Node ===")
            state = await flights_node(state)
            print(f"Flights found: {len(state.get('flights', []))}")
        
        if 'places' in nodes_to_call:
            print("\n=== STEP 5b: Places Node ===")
            state = await places_node(state)
            print(f"Places found: {len(state.get('places', []))}")
        
        if 'restaurants' in nodes_to_call:
            print("\n=== STEP 5c: Restaurants Node ===")
            state = await restaurants_node(state)
            print(f"Restaurants found: {len(state.get('restaurants', []))}")
        
        if 'hotel' in nodes_to_call:
            print("\n=== STEP 5d: Hotel Node ===")
            state = await hotel_node(state)
            print(f"Hotel info: {state.get('hotel', {}).get('name', 'None')}")
        
        if 'budget' in nodes_to_call:
            print("\n=== STEP 5e: Budget Node ===")
            state = await budget_node(state)
            print(f"Total budget: ${state.get('budget', {}).get('total', 0)}")
        
        print("\n=== STEP 6: Reviews Node ===")
        state = await reviews_node(state)
        
        # After running the reviews node, print the results
        print("\n=== Review Insights ===")
        for place in state.get("places", []):
            if "review_insights" in place:
                print(f"\n{place['name']}:")
                print(f"Total Available Reviews: {place['review_insights'].get('total_available_reviews', 0)}")
                print(f"Analyzed Reviews: {place['review_insights'].get('analyzed_reviews', 0)}")
                print(f"Average Rating: {place['review_insights'].get('average_rating', 0)}")
                print(f"Review Distribution: {place['review_insights'].get('review_distribution', {})}")
                print(f"Analysis: {place['review_insights'].get('analysis', '')}")

        for restaurant in state.get("restaurants", []):
            if "review_insights" in restaurant:
                print(f"\n{restaurant['name']}:")
                print(f"Total Available Reviews: {restaurant['review_insights'].get('total_available_reviews', 0)}")
                print(f"Analyzed Reviews: {restaurant['review_insights'].get('analyzed_reviews', 0)}")
                print(f"Average Rating: {restaurant['review_insights'].get('average_rating', 0)}")
                print(f"Review Distribution: {restaurant['review_insights'].get('review_distribution', {})}")
                print(f"Analysis: {restaurant['review_insights'].get('analysis', '')}")

        hotel = state.get("hotel", {})
        if "review_insights" in hotel:
            print(f"\n{hotel['name']}:")
            print(f"Total Available Reviews: {hotel['review_insights'].get('total_available_reviews', 0)}")
            print(f"Analyzed Reviews: {hotel['review_insights'].get('analyzed_reviews', 0)}")
            print(f"Average Rating: {hotel['review_insights'].get('average_rating', 0)}")
            print(f"Review Distribution: {hotel['review_insights'].get('review_distribution', {})}")
            print(f"Analysis: {hotel['review_insights'].get('analysis', '')}")
        
        # Step 7: Summary Node
        print("\n=== STEP 7: Summary Node ===")
        state = await summary_node(state)
        print("\nGENERATED ITINERARY:")
        print("=" * 80)
        print(state.get("itinerary", "No itinerary generated"))
        print("=" * 80)
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_pipeline_step_by_step()) 