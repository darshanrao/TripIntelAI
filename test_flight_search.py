from datetime import datetime, timedelta
from app.schemas.trip_schema import TripMetadata
from app.nodes.agents.flights_node import flights_node

async def test_flight_search():
    # Create test metadata
    start_date = datetime.now() + timedelta(days=30)  # Plan a month in advance
    end_date = start_date + timedelta(days=7)  # One week trip
    
    metadata = TripMetadata(
        source="New York",
        destination="London",
        start_date=start_date,
        end_date=end_date,
        num_people=2,
        preferences=["sightseeing", "history"]
    )
    
    # Create state
    state = {
        "metadata": metadata
    }
    
    # Run flights node
    result = await flights_node(state)
    
    # Check if we got flights
    flights = result.get("flights", [])
    if not flights:
        print("No flights found or error occurred.")
        if "error" in result:
            print(f"Error: {result['error']}")
        return
    
    # Print the flight options
    print(f"\nFound {len(flights)} flight options:")
    for i, flight in enumerate(flights[:5]):  # Print up to 5 flights
        print(f"\nOption {i+1}:")
        print(f"  Airline: {flight.get('airline')}")
        print(f"  Flight: {flight.get('flight_number')}")
        print(f"  Departure: {flight.get('departure_time')}")
        print(f"  Arrival: {flight.get('arrival_time')}")
        print(f"  Price: ${flight.get('price')}")
    
    return result

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_flight_search()) 