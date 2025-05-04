from typing import Dict, Any, Optional, List
import random
from datetime import datetime, timedelta
import os
import requests
from pydantic import BaseModel
from app.schemas.trip_schema import Flight, TripMetadata
from app.nodes.agents.common import GraphState, generate_mock_datetime

class FlightSegment(BaseModel):
    from_airport: str
    to_airport: str
    departure: str
    arrival: str
    carrier_code: str
    duration: str

class FlightOption(BaseModel):
    price: str
    currency: str
    segments: List[FlightSegment]

class AmadeusFlightSearch:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.token = None
        self.token_expiry = None
        
    def _get_token(self):
        """Get or refresh the access token"""
        if self.token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.token
            
        url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.api_secret
        }
        
        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            token_data = response.json()
            
            self.token = token_data["access_token"]
            # Set token expiry (subtract 5 minutes for safety margin)
            self.token_expiry = datetime.now() + timedelta(seconds=token_data["expires_in"] - 300)
            
            return self.token
        except Exception as e:
            print(f"Error getting Amadeus token: {e}")
            return None
            
    def get_iata_code(self, city_name: str) -> str:
        """Get IATA code for a city (simplified version)"""
        # This is a simplified version. In production, use the Amadeus API
        # to get actual IATA codes
        city_codes = {
            "new york": "NYC",
            "boston": "BOS",
            "los angeles": "LAX",
            "san francisco": "SFO",
            "chicago": "CHI",
            "miami": "MIA",
            "london": "LON",
            "paris": "PAR",
            "tokyo": "TYO",
            "sydney": "SYD"
        }
        return city_codes.get(city_name.lower(), city_name[:3].upper())
    
    def search_flights(
        self,
        origin_city: str,
        destination_city: str,
        departure_date: str,
        return_date: str = None,
        adults: int = 1,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for flights using Amadeus API"""
        origin = self.get_iata_code(origin_city)
        destination = self.get_iata_code(destination_city)
        
        # Get access token
        token = self._get_token()
        if not token:
            return []
            
        url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": adults,
            "max": max_results,
            "currencyCode": "USD"
        }
        
        if return_date:
            params["returnDate"] = return_date
        
        raw_data = []
        
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 429:
                raise Exception("Rate limited: Too many flight searches. Try again later.")
            response.raise_for_status()
            
            for i, offer in enumerate(response.json().get("data", []), start=1):
                price = f"{offer['price']['total']} {offer['price']['currency']}"
                for itinerary in offer["itineraries"]:
                    for segment in itinerary["segments"]:
                        flat_row = {
                            "option": i,
                            "price": price,
                            "from": segment["departure"]["iataCode"],
                            "to": segment["arrival"]["iataCode"],
                            "departure": segment["departure"]["at"],
                            "arrival": segment["arrival"]["at"],
                            "airline": segment["carrierCode"],
                            "duration": segment["duration"]
                        }
                        raw_data.append(flat_row)
            return raw_data
        except Exception as e:
            print(f"Error searching flights: {e}")
            return []

async def flights_node(state: GraphState) -> GraphState:
    """
    Find flight options for the trip.
    Uses the Amadeus API to find real flights, with fallback to mock data.
    
    Args:
        state: Current state containing trip metadata
        
    Returns:
        Updated state with flight options
    """
    metadata: Optional[TripMetadata] = state.get("metadata")
    
    if not metadata or not metadata.start_date or not metadata.end_date:
        state["flights"] = []
        return state
    
    # Format dates for API
    start_date_str = metadata.start_date.strftime("%Y-%m-%d")
    end_date_str = metadata.end_date.strftime("%Y-%m-%d")
    
    try:
        # Initialize the Amadeus API client
        api_key = os.getenv("AMADEUS_API_KEY")
        api_secret = os.getenv("AMADEUS_SECRET_KEY")
        
        if not api_key or not api_secret:
            # Fall back to mock data if API keys are not available
            print("Amadeus API credentials not found. Using mock flight data.")
            return await _generate_mock_flights(state)
        
        flight_client = AmadeusFlightSearch(api_key=api_key, api_secret=api_secret)
        
        # Search for flights
        flights_data = flight_client.search_flights(
            origin_city=metadata.source,
            destination_city=metadata.destination,
            departure_date=start_date_str,
            return_date=end_date_str,
            adults=metadata.num_people,
            max_results=5
        )
        
        # If no flights found, use mock data
        if not flights_data:
            print(f"No flights found between {metadata.source} and {metadata.destination}. Using mock data.")
            return await _generate_mock_flights(state)
        
        # Process the flight data into our schema
        flight_options = []
        
        # Group by option
        options = {}
        for flight in flights_data:
            option_num = flight.get("option")
            if option_num not in options:
                options[option_num] = []
            options[option_num].append(flight)
        
        # Create Flight objects for each option (outbound and return)
        for option_num, segments in options.items():
            for segment in segments:
                # Parse price
                price_parts = segment.get("price", "0 USD").split()
                price = float(price_parts[0]) if len(price_parts) > 0 else 0
                
                # Parse dates
                try:
                    departure_time = datetime.fromisoformat(segment.get("departure").replace('Z', '+00:00'))
                    arrival_time = datetime.fromisoformat(segment.get("arrival").replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    # If date parsing fails, use the trip dates
                    departure_time = metadata.start_date
                    arrival_time = metadata.start_date + timedelta(hours=2)
                
                # Create Flight object
                flight = Flight(
                    airline=segment.get("airline", "Unknown"),
                    flight_number=f"{segment.get('airline', 'X')}{random.randint(100, 999)}",
                    departure_time=departure_time,
                    arrival_time=arrival_time,
                    price=price
                )
                
                flight_options.append(flight)
        
        # Sort by price
        flight_options.sort(key=lambda x: x.price)
        
        # Add to state
        # We need to convert Flight objects to dictionaries
        state["flights"] = [flight.model_dump() for flight in flight_options]
        
        return state
    
    except Exception as e:
        print(f"Error in flights_node: {e}")
        # Fall back to mock data if an error occurs
        return await _generate_mock_flights(state)

async def _generate_mock_flights(state: GraphState) -> GraphState:
    """Generate mock flight data as a fallback"""
    metadata = state.get("metadata")
    
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
    
    # Generate return flights
    for i in range(3):  # Generate 3 return flight options
        airline = random.choice(airlines)
        flight_number = f"{airline[0]}{random.randint(100, 999)}"
        departure_time = generate_mock_datetime(metadata.end_date, 16 + i * 2)
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
    
    # Add to state - use model_dump() instead of dict()
    state["flights"] = [flight.model_dump() for flight in flight_options]
    
    return state 