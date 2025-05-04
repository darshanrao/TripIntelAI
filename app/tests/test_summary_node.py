import asyncio
import json
from datetime import datetime, timedelta
from app.nodes.summary_node import summary_node
from app.schemas.trip_schema import (
    TripMetadata, Flight, Hotel, Place, Restaurant, Budget
)

async def test_summary_node():
    """Test the summary node functionality"""
    # Create test data
    start_date = datetime.now()
    end_date = start_date + timedelta(days=3)
    
    # Create metadata
    metadata = TripMetadata(
        source="Boston",
        destination="New York",
        start_date=start_date,
        end_date=end_date,
        num_people=2,
        preferences=["museums", "dining", "history"]
    )
    
    # Create flights
    flights = [
        Flight(
            airline="JetBlue",
            flight_number="B123",
            departure_time=start_date.replace(hour=8),
            arrival_time=start_date.replace(hour=10),
            price=200.0
        ),
        Flight(
            airline="Delta",
            flight_number="D456",
            departure_time=end_date.replace(hour=18),
            arrival_time=end_date.replace(hour=20),
            price=180.0
        )
    ]
    
    # Create hotel
    hotel = Hotel(
        name="The Plaza Hotel",
        rating=4.8,
        price_per_night=300.0,
        location="Central Park South",
        amenities=["WiFi", "Pool", "Gym", "Room Service"]
    )
    
    # Create places
    places = [
        Place(
            name="Central Park",
            description="Iconic park in the heart of Manhattan",
            rating=4.8,
            price=0.0,
            location="Manhattan",
            category="Park"
        ),
        Place(
            name="Empire State Building",
            description="Historic 102-story skyscraper",
            rating=4.7,
            price=42.0,
            location="Midtown",
            category="Landmark"
        ),
        Place(
            name="Metropolitan Museum of Art",
            description="One of the world's largest and finest art museums",
            rating=4.8,
            price=25.0,
            location="Upper East Side",
            category="Museum"
        ),
        Place(
            name="Statue of Liberty",
            description="Iconic statue on Liberty Island",
            rating=4.7,
            price=23.5,
            location="Liberty Island",
            category="Monument"
        ),
        Place(
            name="Museum of Modern Art",
            description="World's most influential modern art museum",
            rating=4.6,
            price=25.0,
            location="Midtown",
            category="Museum"
        )
    ]
    
    # Create restaurants
    restaurants = [
        Restaurant(
            name="Katz's Delicatessen",
            cuisine="American Deli",
            rating=4.5,
            price_level=2,
            location="Lower East Side",
            description="Famous for pastrami sandwiches"
        ),
        Restaurant(
            name="Joe's Pizza",
            cuisine="Pizza",
            rating=4.7,
            price_level=1,
            location="Greenwich Village",
            description="Classic NY-style pizza slices"
        ),
        Restaurant(
            name="Le Bernardin",
            cuisine="French Seafood",
            rating=4.9,
            price_level=4,
            location="Midtown",
            description="Upscale French seafood restaurant"
        ),
        Restaurant(
            name="Grimaldi's Pizzeria",
            cuisine="Pizza",
            rating=4.6,
            price_level=2,
            location="Brooklyn",
            description="Famous brick oven pizza"
        ),
        Restaurant(
            name="The Halal Guys",
            cuisine="Middle Eastern",
            rating=4.5,
            price_level=1,
            location="Midtown",
            description="Popular street food cart"
        )
    ]
    
    # Create budget
    budget = Budget(
        flights_total=760.0,
        hotel_total=900.0,
        daily_food_estimate=100.0,
        activities_estimate=200.0,
        total=2000.0
    )
    
    # Add route information
    route = {
        "distance_km": 350,
        "duration_hours": 4.5,
        "directions": "Take I-90 E from Boston to New York",
        "map_url": "https://maps.google.com/?saddr=Boston&daddr=New+York"
    }
    
    # Prepare state with model_dump instead of dict
    state = {
        "metadata": metadata.model_dump(),
        "flights": [flight.model_dump() for flight in flights],
        "hotel": hotel.model_dump(),
        "places": [place.model_dump() for place in places],
        "restaurants": [restaurant.model_dump() for restaurant in restaurants],
        "budget": budget.model_dump(),
        "route": route
    }
    
    # Run summary node
    result = await summary_node(state)
    
    # Print the result in a readable format
    if "error" in result["itinerary"]:
        print("Error in itinerary generation:", result["itinerary"]["error"])
        if "raw_response" in result["itinerary"]:
            print("\nRaw response:")
            print(result["itinerary"]["raw_response"][:500] + "..." if len(result["itinerary"]["raw_response"]) > 500 else result["itinerary"]["raw_response"])
    else:
        print(json.dumps(result["itinerary"], indent=2))
    
    # Verify the structure
    if "error" not in result["itinerary"]:
        assert "trip_summary" in result["itinerary"]
        assert "daily_itinerary" in result["itinerary"]
        
        # Check that there are entries for each day
        day_keys = [f"day_{i+1}" for i in range((end_date - start_date).days + 1)]
        for day_key in day_keys:
            assert day_key in result["itinerary"]["daily_itinerary"]
            
        # Check for activity structure in day 1
        day1 = result["itinerary"]["daily_itinerary"]["day_1"]
        assert "activities" in day1
        assert len(day1["activities"]) > 0
        
        # Check for time information in activities
        for activity in day1["activities"]:
            assert "time" in activity
            assert "duration_minutes" in activity
            assert "type" in activity
            assert "details" in activity
    
    return result

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_summary_node()) 