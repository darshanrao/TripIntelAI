import asyncio
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from app.nodes.agent_nodes_1 import flights_node
from app.schemas.trip_schema import TripMetadata

# Load environment variables
load_dotenv()

async def test_flights_api():
    """Test the flights node with Amadeus API integration"""
    print("Testing Amadeus Flight API...")
    
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
    # Check if Amadeus API keys are set
    api_key = os.getenv("AMADEUS_API_KEY")
    api_secret = os.getenv("AMADEUS_SECRET_KEY")
    
    if not api_key or not api_secret:
        print("WARNING: Amadeus API credentials not found in environment variables.")
        print("Set AMADEUS_API_KEY and AMADEUS_SECRET_KEY to test with real flight data.")
        print("The test will fall back to mock flight data.")
    
    # Run the test
    asyncio.run(test_flights_api()) 