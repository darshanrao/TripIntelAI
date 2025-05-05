import pytest
from fastapi.testclient import TestClient
from app.main import app
import json
from datetime import datetime, timedelta
import asyncio

# Create a test client
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Setup and teardown for each test"""
    # Setup - nothing needed
    yield
    # Teardown - clear event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            pending = asyncio.all_tasks(loop)
            loop.run_until_complete(asyncio.gather(*pending))
    except Exception:
        pass

def test_basic_chat_interaction():
    """Test basic chat interaction with travel query"""
    # Create a simple travel query
    request_data = {
        "message": "I want to plan a trip to Paris for 2 people from July 1st to July 7th 2024",
        "conversation_id": None,
        "interaction_type": "chat",
        "metadata": {
            "test_mode": True  # Add test mode flag
        }
    }
    
    response = client.post("/interact", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] == True
    assert data["conversation_id"] is not None
    
    # The response should be either validation, flight_selection, or feedback
    assert data["interaction_type"] in ["validation", "flight_selection", "feedback"]
    
    # If we get validation, we need to handle it
    if data["interaction_type"] == "validation":
        # Get the conversation ID from the first response
        conv_id = data["conversation_id"]
        
        # Send another request with the same conversation ID
        request_data = {
            "message": "Yes, that's correct. I want to go to Paris.",
            "conversation_id": conv_id,
            "interaction_type": "chat",
            "metadata": {
                "test_mode": True
            }
        }
        
        response = client.post("/interact", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert data["interaction_type"] in ["flight_selection", "feedback"]
    
    return data["conversation_id"]

def test_flight_selection():
    """Test flight selection process"""
    # First create a conversation
    conv_id = test_basic_chat_interaction()
    
    # Select a flight (assuming index 0)
    request_data = {
        "conversation_id": conv_id,
        "interaction_type": "flight_selection",
        "selection_data": {
            "flight_index": 0
        },
        "metadata": {
            "test_mode": True
        }
    }
    
    response = client.post("/interact", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] == True
    
    # After flight selection, we should get the itinerary
    assert "data" in data
    if "itinerary" in data["data"]:
        assert isinstance(data["data"]["itinerary"], (str, dict))
    
    return conv_id

def test_feedback_interaction():
    """Test providing feedback on the itinerary"""
    # First get an itinerary
    conv_id = test_flight_selection()
    
    # Provide feedback
    request_data = {
        "conversation_id": conv_id,
        "interaction_type": "feedback",
        "message": "Can you add more museums to the itinerary?",
        "selection_data": {
            "category_id": "3",  # Activities modification
            "specific_feedback": "Add more museums"
        },
        "metadata": {
            "test_mode": True
        }
    }
    
    response = client.post("/interact", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] == True
    assert "data" in data
    
    # Should have updated itinerary
    if "itinerary" in data["data"]:
        assert isinstance(data["data"]["itinerary"], (str, dict))

def test_analyze_input():
    """Test the analyze-input endpoint"""
    request_data = {
        "input": "I want to visit Tokyo for 5 days starting December 1st 2024",
        "user_id": "test_user",
        "metadata": {
            "test_mode": True
        }
    }
    
    response = client.post("/analyze-input", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] == True
    assert "data" in data
    assert "extracted_data" in data["data"]
    
    # Verify extracted data
    extracted = data["data"]["extracted_data"]
    assert "destination" in extracted
    assert extracted["destination"].lower() == "tokyo"

def test_save_and_retrieve_trip():
    """Test saving and retrieving a trip"""
    # First create a trip through normal interaction
    conv_id = test_flight_selection()
    
    # Get the itinerary
    response = client.get(f"/conversations/{conv_id}")
    assert response.status_code == 200
    
    # Save the trip
    trip_data = {
        "destination": "Paris",
        "start_date": "2024-07-01",
        "end_date": "2024-07-07",
        "num_travelers": 2,
        "metadata": {
            "test_mode": True
        }
    }
    
    response = client.post("/trips", json=trip_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "trip_id" in data
    
    # Retrieve the saved trip
    trip_id = data["trip_id"]
    response = client.get(f"/trips/{trip_id}")
    assert response.status_code == 200
    
    # Verify trip data
    saved_trip = response.json()
    assert saved_trip["trip_id"] == trip_id
    assert "trip_data" in saved_trip

def test_error_handling():
    """Test error handling for invalid inputs"""
    # Test with invalid conversation ID
    request_data = {
        "conversation_id": "invalid_id",
        "message": "Hello",
        "interaction_type": "chat",
        "metadata": {
            "test_mode": True
        }
    }
    
    response = client.post("/interact", json=request_data)
    assert response.status_code == 200  # API returns 200 with error in response
    data = response.json()
    assert data["success"] == False
    
    # Test with invalid flight selection
    request_data = {
        "conversation_id": "some_id",
        "interaction_type": "flight_selection",
        "selection_data": {
            "flight_index": 999  # Invalid index
        },
        "metadata": {
            "test_mode": True
        }
    }
    
    response = client.post("/interact", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == False

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 