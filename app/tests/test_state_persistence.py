import os
import asyncio
import uuid  # For generating a real session_id
from app.graph.trip_planner_graph import TripPlannerGraph
from app.utils.logger import logger
from app.nodes.trip_validator_node import process_user_response
import json

async def test_state_persistence():
    """Test state persistence in the trip planner graph."""
    print("\n=== Testing State Persistence ===")
    
    # Create graph instance
    graph = TripPlannerGraph()
    
    # Initial state with minimal information
    initial_state = {
        "session_id": "test-session-123",  # Add session_id for Supabase
        "query": "I want to plan a trip to Tokyo and I like anime museums",
        "raw_query": "I want to plan a trip to Tokyo and I like anime museums",
        "metadata": {
            "destination": "Tokyo",
            "preferences": ["anime museums"]
        },
        "is_valid": False,
        "next_question": None,
        "error": None,
        "thought": None,
        "action": "collect_info",
        "action_input": {"field": "source"},
        "observation": None,
        "nodes_to_call": [],
        "flights": [],
        "places": [],
        "restaurants": [],
        "hotel": {},
        "daily_itineraries": [],
        "visited_places": set(),
        "visited_restaurants": set()
    }
    
    try:
        # First run - should stop at validator asking questions
        print("\n1. Starting first run...")
        result = await graph.process(initial_state)
        
        # Verify that validator is asking for information
        assert result.get("next_question") is not None, "Validator should ask a question"
        assert result.get("is_valid") is False, "State should not be valid yet"
        assert result.get("action") == "collect_info", "Should be collecting information"
        
        # Save the state after first run
        print("\nSaving state after first run...")
        await graph.save_state(result)
        
        # Simulate user response
        print("\n2. Simulating user response...")
        user_response = "I'll be traveling from New York"
        updated_state = await process_user_response(result, user_response)
        
        # Verify state was updated
        assert updated_state.get("metadata", {}).get("source") == "New York", "Source should be updated"
        print(f"Updated state after user response: {updated_state}")
        
        # Save the updated state
        print("\nSaving updated state...")
        await graph.save_state(updated_state)
        
        # Load the state to verify persistence
        print("\n3. Loading saved state...")
        loaded_state = await graph.load_state(updated_state.get("session_id"))
        
        # Verify loaded state matches saved state
        assert loaded_state is not None, "Should be able to load saved state"
        assert loaded_state.get("metadata", {}).get("source") == "New York", "Loaded state should have saved source"
        print(f"Loaded state: {loaded_state}")
        
        print("\nState persistence test completed successfully!")
        
    except Exception as e:
        print(f"\nError in test: {str(e)}")
        raise

async def test_process_response_loop():
    """Test the process_response loop and state updates with Supabase persistence."""
    print("\n=== Testing Process Response Loop ===")
    
    # In a real chatbot, session_id should be generated once per chat session and reused for all messages in that session.
    session_id = str(uuid.uuid4())
    print(f"Generated session_id for this test: {session_id}")
    
    # Create graph instance for Supabase operations
    graph = TripPlannerGraph()
    
    # Initial state with minimal information
    initial_state = {
        "session_id": session_id,  # Use a valid UUID for session_id
        "query": "I want to plan a trip to Tokyo and I like anime museums",
        "raw_query": "I want to plan a trip to Tokyo and I like anime museums",
        "metadata": {
            "destination": "Tokyo",
            "preferences": ["anime museums"]
        },
        "is_valid": False,
        "next_question": None,
        "error": None,
        "thought": None,
        "action": "collect_info",
        "action_input": {"field": "source"},
        "observation": None,
        "nodes_to_call": [],
        "flights": [],
        "places": [],
        "restaurants": [],
        "hotel": {},
        "daily_itineraries": [],
        "visited_places": set(),
        "visited_restaurants": set()
    }
    
    try:
        # Save initial state
        print("\nSaving initial state...")
        await graph.save_state(initial_state)
        print(f"Session ID: {session_id}")
        
        # Simulate user responses for each required field
        test_responses = {
            "source": "I'll be traveling from Los Angeles",
            "start_date": "I want to start on June 1st, 2025",
            "end_date": "I want to end on June 2nd, 2025",
            "num_people": "There will be 2 people traveling",
            "preferences": "I'm interested in anime museums and trying local food"
        }
        
        current_state = initial_state
        for field, response in test_responses.items():
            print(f"\nProcessing response for {field}: {response}")
            
            # Update action_input to indicate which field we're collecting
            current_state["action_input"] = {"field": field}
            
            # Process the user response
            updated_state = await process_user_response(current_state, response)
            
            # Verify state was updated
            assert updated_state.get("metadata", {}).get(field) is not None, f"{field} should be updated"
            print(f"Updated metadata for {field}: {updated_state.get('metadata', {}).get(field)}")
            
            # Save the updated state to Supabase
            print(f"Saving state to Supabase after {field} update...")
            await graph.save_state(updated_state)
            
            # Load the state from Supabase to verify persistence
            print(f"Loading state from Supabase to verify {field} was saved...")
            loaded_state = await graph.load_state(session_id)
            assert loaded_state is not None, "Should be able to load saved state"
            assert loaded_state.get("metadata", {}).get(field) == updated_state.get("metadata", {}).get(field), f"Loaded state should have saved {field}"
            print(f"Verified {field} was saved correctly in Supabase")
            
            current_state = updated_state
        
        # Final verification
        print("\nFinal state verification...")
        assert current_state.get("is_valid") is True, "State should be valid after all fields are filled"
        print("All required fields are filled and state is valid")
        print(f"Final metadata: {current_state.get('metadata')}")
        
        # Final Supabase verification
        print("\nFinal Supabase verification...")
        final_loaded_state = await graph.load_state(session_id)
        assert final_loaded_state is not None, "Should be able to load final state"
        assert final_loaded_state.get("metadata") == current_state.get("metadata"), "Final state in Supabase should match current state"
        print("Final state verified in Supabase")
        
        print("\nProcess response loop test completed successfully!")
        
    except Exception as e:
        print(f"\nError in test: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(test_process_response_loop()) 