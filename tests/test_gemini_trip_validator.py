import asyncio
import os
import pytest
from datetime import datetime
from dotenv import load_dotenv
from app.nodes.trip_validator_node import trip_validator_node, process_user_response
from app.schemas.trip_schema import TripMetadata

# Load environment variables from .env file
load_dotenv()

# Ensure GEMINI_API_KEY is set
if not os.getenv("GEMINI_API_KEY"):
    raise ValueError("GEMINI_API_KEY environment variable is not set. Please add it to your .env file.")

@pytest.mark.asyncio
async def test_trip_validator():
    # Test Case 1: Initial validation with complete information
    state1 = {
        "raw_query": "I want to go to Paris from New York for 5 days starting May 15th, 2024. I'm interested in museums and food.",
        "metadata": TripMetadata(
            source="New York",
            destination="Paris",
            start_date=datetime(2024, 5, 15),
            end_date=datetime(2024, 5, 20),
            num_people=2,
            preferences=["museums", "food"]
        )
    }
    
    # Test Case 2: Initial validation with missing information
    state2 = {
        "raw_query": "I want to visit Paris",
        "metadata": TripMetadata(
            source=None,
            destination="Paris",
            start_date=None,
            end_date=None,
            num_people=None,
            preferences=[]
        )
    }
    
    # Test Case 3: Processing user response for missing field
    state3 = {
        "raw_query": "I want to visit Paris",
        "metadata": TripMetadata(
            source=None,
            destination="Paris",
            start_date=None,
            end_date=None,
            num_people=None,
            preferences=[]
        ),
        "action_input": {"field": "source"},
        "user_response": "I'll be traveling from New York City"
    }
    
    # Run tests
    test_cases = [
        ("Complete Information", state1),
        ("Missing Information", state2),
        ("User Response Processing", state3)
    ]
    
    for test_name, state in test_cases:
        print(f"\nTesting {test_name}...")
        if test_name == "User Response Processing":
            result = await process_user_response(state, state["user_response"])
        else:
            result = await trip_validator_node(state)
        
        # Verify the result
        assert "error" not in result or not result["error"], f"Error in {test_name}: {result.get('error')}"
        
        if test_name == "Complete Information":
            assert result["is_valid"] == True, f"Complete information should be valid"
            assert result["action"] == "complete", f"Complete information should have 'complete' action"
        elif test_name == "Missing Information":
            assert result["is_valid"] == False, f"Missing information should be invalid"
            assert result["action"] == "collect_info", f"Missing information should have 'collect_info' action"
            assert "next_question" in result, f"Missing information should have a next question"
        elif test_name == "User Response Processing":
            assert result["action"] in ["update_metadata", "ask_clarification"], f"Invalid action for user response"
            if result["action"] == "update_metadata":
                assert result["metadata"].source in ["New York", "New York City"] or "New York" in result["metadata"].source, f"Source not updated correctly: {result['metadata'].source}"
        
        print(f"{test_name} test passed!")
        print(f"Action: {result.get('action')}")
        print(f"Thought: {result.get('thought')}")
        if "next_question" in result:
            print(f"Next Question: {result['next_question']}")

if __name__ == "__main__":
    asyncio.run(test_trip_validator()) 