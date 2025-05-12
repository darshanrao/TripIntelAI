import pytest
from datetime import datetime, timedelta
from app.nodes.agents.flights_node import flights_node, GraphState
from app.schemas.trip_schema import TripMetadata
from app.nodes.agents.common import generate_mock_datetime

@pytest.mark.asyncio
async def test_flights_node():
    # Create test metadata
    tomorrow = datetime.now() + timedelta(days=1)
    metadata = TripMetadata(
        source="San Francisco",
        destination="New York",
        start_date=tomorrow,
        end_date=tomorrow + timedelta(days=3),
        num_people=1,
        preferences=["direct flights", "morning departures"]
    )
    
    # Create initial state
    state = GraphState({
        "metadata": metadata,
        "flights": []
    })
    
    # Test the flights node
    result_state = await flights_node(state)
    
    # Print the results
    print("\nFlight Search Results:")
    print("=====================")
    for flight in result_state["flights"]:
        print(f"\nFlight: {flight['airline']} {flight['flight_number']}")
        print(f"Route: {flight['departure_airport']} ({flight['departure_city']}) → {flight['arrival_airport']} ({flight['arrival_city']})")
        print(f"Departure: {flight['departure_time']}")
        print(f"Arrival: {flight['arrival_time']}")
        print(f"Duration: {flight['duration_minutes']} minutes")
        print(f"Cabin: {flight['cabin_class']}")
        print(f"Price: ${flight['price']}")
        print(f"Aircraft: {flight['aircraft']}")
        print(f"Stops: {flight['stops']}")
        print(f"Baggage Included: {'Yes' if flight['baggage_included'] else 'No'}")
        print("-" * 50)
    
    # Verify the results
    assert "flights" in result_state
    flights = result_state["flights"]
    assert len(flights) > 0
    
    # Check the structure of each flight
    for flight in flights:
        assert "id" in flight
        assert "airline" in flight
        assert "flight_number" in flight
        assert "departure_airport" in flight
        assert "departure_city" in flight
        assert "arrival_airport" in flight
        assert "arrival_city" in flight
        assert "departure_time" in flight
        assert "arrival_time" in flight
        assert "price" in flight
        assert "duration_minutes" in flight
        assert "stops" in flight
        assert "aircraft" in flight
        assert "cabin_class" in flight
        assert "baggage_included" in flight
        
        # Verify specific values
        assert isinstance(flight["price"], (int, float))
        assert isinstance(flight["duration_minutes"], int)
        assert isinstance(flight["stops"], int)
        assert flight["baggage_included"] is True
        
        # Verify departure and arrival times are valid ISO format
        try:
            datetime.fromisoformat(flight["departure_time"])
            datetime.fromisoformat(flight["arrival_time"])
        except ValueError:
            pytest.fail("Invalid datetime format")
        
        # Verify flight numbers are in correct format (e.g., "DL123", "UA456")
        assert len(flight["flight_number"]) >= 3
        assert flight["flight_number"][:2].isalpha()
        assert flight["flight_number"][2:].isdigit()

if __name__ == "__main__":
    pytest.main([__file__]) 