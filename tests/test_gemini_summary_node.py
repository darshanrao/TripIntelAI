import pytest
from datetime import datetime, timedelta
from app.nodes.summary_node import summary_node

@pytest.mark.asyncio
async def test_summary_node():
    # Create test data
    destination = "Los Angeles"
    metadata = {
        "destination": destination,
        "start_date": datetime.now().date(),
        "end_date": (datetime.now() + timedelta(days=3)).date(),
        "duration_days": 3,
        "total_budget": 2000
    }
    
    selected_flights = [
        {
            "source": "SFO",
            "destination": destination,
            "departure_time": datetime.now() + timedelta(hours=2),
            "arrival_time": datetime.now() + timedelta(hours=4),
            "price": 300
        },
        {
            "source": destination,
            "destination": "SFO",
            "departure_time": datetime.now() + timedelta(days=3, hours=2),
            "arrival_time": datetime.now() + timedelta(days=3, hours=4),
            "price": 300
        }
    ]
    
    hotel = {
        "name": "Test Hotel",
        "address": "123 Test St, Los Angeles, CA",
        "price_per_night": 200,
        "check_in": datetime.now() + timedelta(hours=4),
        "check_out": datetime.now() + timedelta(days=3, hours=2)
    }
    
    places = [
        {
            "name": "Test Place 1",
            "address": "456 Test Ave, Los Angeles, CA",
            "rating": 4.5,
            "reviews": ["Great place!", "Must visit!"]
        },
        {
            "name": "Test Place 2",
            "address": "789 Test Blvd, Los Angeles, CA",
            "rating": 4.0,
            "reviews": ["Nice place", "Good experience"]
        }
    ]
    
    restaurants = [
        {
            "name": "Test Restaurant 1",
            "address": "101 Test Rd, Los Angeles, CA",
            "rating": 4.5,
            "reviews": ["Great food!", "Amazing service!"]
        },
        {
            "name": "Test Restaurant 2",
            "address": "202 Test Ln, Los Angeles, CA",
            "rating": 4.0,
            "reviews": ["Good food", "Nice ambiance"]
        }
    ]
    
    budget = {
        "total_budget": 2000,
        "allocated_budget": {
            "flights": 600,
            "hotel": 600,
            "activities": 400,
            "food": 400
        }
    }
    
    route = {
        "source": "SFO",
        "destination": destination,
        "distance": 350,
        "duration": 120
    }
    
    # Create state
    state = {
        "metadata": metadata,
        "selected_flights": selected_flights,
        "hotel": hotel,
        "places": places,
        "restaurants": restaurants,
        "budget": budget,
        "route": route
    }
    
    # Call summary node
    result = await summary_node(state)
    
    # Verify result
    assert "itinerary" in result
    assert "trip_summary" in result["itinerary"]
    assert "daily_itinerary" in result["itinerary"]
    
    # Verify trip summary
    trip_summary = result["itinerary"]["trip_summary"]
    assert trip_summary["destination"] == destination
    assert trip_summary["duration_days"] == 3
    assert trip_summary["total_budget"] == 2000
    
    # Verify daily itinerary
    daily_itinerary = result["itinerary"]["daily_itinerary"]
    assert len(daily_itinerary) >= 3  # 3 or more days
    
    # Verify first day has arrival flight
    day_1 = daily_itinerary["day_1"]
    assert any(
        activity["type"] == "flight" and
        (activity["details"].lower().find("arrive") != -1 or
         activity["details"].lower().find("arrival") != -1)
        for activity in day_1["activities"]
    ), "First day should include arrival flight"
    
    # Verify last day has departure flight
    last_day = daily_itinerary[f"day_{len(daily_itinerary)}"]
    assert any(
        activity["type"] == "flight" and
        (activity["details"].lower().find("depart") != -1 or
         activity["details"].lower().find("departure") != -1)
        for activity in last_day["activities"]
    ), "Last day should include departure flight"
    
    # Verify hotel check-in and check-out
    assert any(
        activity["type"] == "hotel" and
        activity["details"].lower().find("check-in") != -1
        for activity in day_1["activities"]
    ), "First day should include hotel check-in"
    
    assert any(
        activity["type"] == "hotel" and
        activity["details"].lower().find("check-out") != -1
        for activity in last_day["activities"]
    ), "Last day should include hotel check-out"
    
    print("Summary node test passed!") 