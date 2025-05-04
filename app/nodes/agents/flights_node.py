from typing import Dict, Any, Optional
import random
from datetime import timedelta
from app.schemas.trip_schema import Flight, TripMetadata
from app.nodes.agents.common import GraphState, generate_mock_datetime

async def flights_node(state: GraphState) -> GraphState:
    """
    Find flight options for the trip.
    
    Args:
        state: Current state containing trip metadata
        
    Returns:
        Updated state with flight options
    """
    metadata: Optional[TripMetadata] = state.get("metadata")
    
    if not metadata or not metadata.start_date or not metadata.end_date:
        state["flights"] = []
        return state
    
    # Mock flight data
    airlines = ["JetBlue", "Delta", "United", "American", "Southwest"]
    flight_options = []
    
    for i in range(3):  # Generate 3 flight options
        airline = random.choice(airlines)
        flight_number = f"{airline[0]}{random.randint(100, 999)}"
        departure_time = generate_mock_datetime(metadata.start_date, 8 + i * 2)
        flight_duration = timedelta(hours=random.randint(1, 5), minutes=random.randint(0, 59))
        arrival_time = departure_time + flight_duration
        price = round(random.uniform(150, 400), 2)
        
        flight = Flight(
            airline=airline,
            flight_number=flight_number,
            departure_time=departure_time,
            arrival_time=arrival_time,
            price=price
        )
        
        flight_options.append(flight)
    
    # Sort by price
    flight_options.sort(key=lambda x: x.price)
    
    # Add to state
    state["flights"] = [flight.dict() for flight in flight_options]
    
    return state 