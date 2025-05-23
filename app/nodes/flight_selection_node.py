from typing import Dict, Any, List, Optional, TypedDict
import json

class GraphState(TypedDict, total=False):
    """State for the LangGraph pipeline."""
    flights: List[Dict[str, Any]]
    selected_flights: List[Dict[str, Any]]
    error: Optional[str]

async def display_flight_options(flights: List[Dict[str, Any]], limit: int = 5) -> None:
    """
    Display flight options to the user in a formatted way.
    
    Args:
        flights: List of flight dictionaries
        limit: Maximum number of flights to display
    """
    if not flights:
        print("No flight options available.")
        return
    
    # Limit the number of flights to display
    flights_to_display = flights[:limit]
    
    print("\n✈️  Available Flight Options ✈️")
    print("-" * 80)
    
    for i, flight in enumerate(flights_to_display, start=1):
        # Format departure and arrival times
        departure_time = flight.get("departure_time", "Unknown")
        arrival_time = flight.get("arrival_time", "Unknown")
        
        # Format price with currency
        price = flight.get("price", 0)
        currency = "USD"  # Default currency
        
        # Build flight display
        print(f"Option {i}:")
        print(f"  Airline: {flight.get('airline', 'Unknown')}")
        print(f"  Flight: {flight.get('flight_number', 'Unknown')}")
        print(f"  Departure: {departure_time}")
        print(f"  Arrival: {arrival_time}")
        print(f"  Price: ${price:.2f} {currency}")
        print("-" * 40)
    
    # Print as JSON for developers/debugging
    print("\nFlight options (JSON format):")
    print(json.dumps(flights_to_display, indent=2, default=str))

async def get_user_flight_selection(flights: List[Dict[str, Any]], limit: int = 5) -> int:
    """
    Get user selection of flight option.
    Now automatically returns the first flight option (index 0).
    
    Args:
        flights: List of flight dictionaries
        limit: Maximum number of flight options
        
    Returns:
        Index of selected flight (0-based)
    """
    # Always select the first flight (index 0)
    print("\nAutomatically selecting the first flight option.")
    return 0

async def flight_selection_node(state: GraphState) -> GraphState:
    """
    Interactive node that displays flight options and automatically selects the first one.
    
    Args:
        state: Current state containing flight options
        
    Returns:
        Updated state with selected flight
    """
    # Get the flights from state
    flights = state.get("flights", [])
    
    if not flights:
        state["error"] = "No flight options available."
        state["selected_flights"] = []
        return state
    
    try:
        # Display flight options to the user
        await display_flight_options(flights)
        
        # Automatically select the first flight
        selection_idx = 0
        
        # Update state with selected flight
        selected_flight = flights[selection_idx]
        state["selected_flights"] = [selected_flight]
        
        print(f"\n✅ Automatically selected flight option {selection_idx + 1}.")
        
        return state
    
    except Exception as e:
        print(f"Error in flight selection: {e}")
        state["error"] = f"Error during flight selection: {str(e)}"
        return state 