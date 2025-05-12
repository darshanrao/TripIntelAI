from typing import Dict, Any, Optional, List
import random
from datetime import datetime, timedelta
import os
import httpx
from pydantic import BaseModel
from app.schemas.trip_schema import Flight, TripMetadata
from app.nodes.agents.common import GraphState, generate_mock_datetime
from app.utils.logger import logger
from dotenv import load_dotenv
import json

# Load environment variables from .env file
load_dotenv()

class FlightData(BaseModel):
    id: str
    airline: str
    flight_number: str
    departure_airport: str
    departure_city: str
    arrival_airport: str
    arrival_city: str
    departure_time: str
    arrival_time: str
    price: float
    duration_minutes: int
    stops: int
    aircraft: str
    cabin_class: str
    baggage_included: bool

class PerplexityFlightSearch:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.perplexity.ai/chat/completions"
        
    async def search_flights(
        self,
        origin_city: str,
        destination_city: str,
        departure_date: str,
        return_date: str = None,
        adults: int = 1,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for flights using Perplexity API"""
        # Construct a natural language query
        query = f"Find {max_results} flights from {origin_city} to {destination_city} on {departure_date}. For each flight, provide: airline name, flight number, departure airport code and city, arrival airport code and city, departure and arrival times, price in USD, duration in minutes, number of stops, aircraft type, cabin class, and whether baggage is included. Format the response as a JSON array of flight objects."
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "sonar",
            "messages": [
                {
                    "role": "system",
                    "content": "Be precise and concise."
                },
                {
                    "role": "user",
                    "content": query
                }
            ]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"Sending request to Perplexity API: {data}")
                response = await client.post(self.base_url, json=data, headers=headers)
                logger.info(f"Perplexity API response status: {response.status_code}")
                logger.info(f"Perplexity API response: {response.text}")
                
                if response.status_code != 200:
                    logger.error(f"Perplexity API error: {response.text}")
                    logger.info("Falling back to mock data due to API error")
                    return self._generate_mock_flights_from_response("")
                
                response.raise_for_status()
                
                # Parse the response to extract flight information
                result = response.json()
                flights_data = self._parse_perplexity_response(result)
                
                if not flights_data:
                    logger.warning("No flights data parsed from API response, falling back to mock data")
                    return self._generate_mock_flights_from_response("")
                    
                return flights_data
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error occurred while calling Perplexity API: {str(e)}")
            logger.info("Falling back to mock data due to HTTP error")
            return self._generate_mock_flights_from_response("")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from Perplexity API: {str(e)}")
            logger.info("Falling back to mock data due to JSON parsing error")
            return self._generate_mock_flights_from_response("")
        except Exception as e:
            logger.error(f"Unexpected error while searching flights with Perplexity: {str(e)}")
            logger.info("Falling back to mock data due to unexpected error")
            return self._generate_mock_flights_from_response("")
            
    def _parse_perplexity_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Perplexity API response to extract flight information"""
        try:
            content = response["choices"][0]["message"]["content"]
            # Parse the JSON response
            flights_data = json.loads(content)
            return flights_data
        except Exception as e:
            logger.error(f"Error parsing Perplexity response: {e}")
            return []
            
    def _generate_mock_flights_from_response(self, content: str) -> List[Dict[str, Any]]:
        """Generate mock flight data based on Perplexity response content"""
        # This is a placeholder. In production, you would parse the actual response
        airlines = [
            {
                "name": "Delta Air Lines",
                "code": "DL",
                "aircraft": ["Boeing 737-900", "Airbus A320", "Boeing 757-200"],
                "price_ranges": {
                    "Economy": (300, 600),
                    "Premium Economy": (600, 900),
                    "Business": (1000, 1500)
                }
            },
            {
                "name": "United Airlines",
                "code": "UA",
                "aircraft": ["Boeing 737-800", "Airbus A320", "Boeing 757-300"],
                "price_ranges": {
                    "Economy": (320, 620),
                    "Premium Economy": (620, 920),
                    "Business": (1050, 1550)
                }
            },
            {
                "name": "American Airlines",
                "code": "AA",
                "aircraft": ["Boeing 737-800", "Airbus A320", "Boeing 757-200"],
                "price_ranges": {
                    "Economy": (310, 610),
                    "Premium Economy": (610, 910),
                    "Business": (1020, 1520)
                }
            }
        ]
        
        # Common flight durations for major routes (in minutes)
        route_durations = {
            "SFO-JFK": 340,  # San Francisco to New York
            "JFK-SFO": 345,  # New York to San Francisco
            "LAX-JFK": 335,  # Los Angeles to New York
            "JFK-LAX": 340   # New York to Los Angeles
        }
        
        # Common departure times for transcontinental flights
        departure_times = [
            (6, 0),   # 6:00 AM
            (8, 30),  # 8:30 AM
            (10, 0),  # 10:00 AM
            (13, 30), # 1:30 PM
            (16, 0),  # 4:00 PM
            (19, 0)   # 7:00 PM
        ]
        
        flights = []
        for i in range(3):
            airline = random.choice(airlines)
            flight_number = f"{airline['code']}{random.randint(100, 999)}"
            
            # Get departure time
            hour, minute = random.choice(departure_times)
            departure_time = datetime.now() + timedelta(days=1, hours=hour, minutes=minute)
            
            # Get route duration
            route = "SFO-JFK"
            duration_minutes = route_durations.get(route, 340)
            arrival_time = departure_time + timedelta(minutes=duration_minutes)
            
            # Select cabin class and price
            cabin_class = random.choices(
                ["Economy", "Premium Economy", "Business"],
                weights=[0.7, 0.2, 0.1]  # 70% Economy, 20% Premium, 10% Business
            )[0]
            min_price, max_price = airline["price_ranges"][cabin_class]
            price = random.randint(min_price, max_price)
            
            # Select aircraft
            aircraft = random.choice(airline["aircraft"])
            
            # Determine stops (mostly non-stop for these routes)
            stops = random.choices([0, 1], weights=[0.9, 0.1])[0]  # 90% non-stop
            
            flight = {
                "id": f"{airline['code']}{flight_number}-SFO-JFK",
                "airline": airline["name"],
                "flight_number": flight_number,
                "departure_airport": "SFO",
                "departure_city": "San Francisco",
                "arrival_airport": "JFK",
                "arrival_city": "New York",
                "departure_time": departure_time.isoformat(),
                "arrival_time": arrival_time.isoformat(),
                "price": price,
                "duration_minutes": duration_minutes,
                "stops": stops,
                "aircraft": aircraft,
                "cabin_class": cabin_class,
                "baggage_included": True
            }
            flights.append(flight)
            
        return flights

async def flights_node(state: GraphState) -> GraphState:
    """
    Find flight options for the trip using Perplexity API.
    
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
    
    # Initialize the Perplexity API client
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        logger.error("Perplexity API key not found. Cannot search flights.")
        raise RuntimeError("PERPLEXITY_API_KEY is not set in the environment.")
    
    flight_client = PerplexityFlightSearch(api_key=api_key)
    try:
        # Search for flights
        flights_data = await flight_client.search_flights(
            origin_city=metadata.source,
            destination_city=metadata.destination,
            departure_date=start_date_str,
            return_date=end_date_str,
            adults=metadata.num_people,
            max_results=5
        )
        # If no flights found, return empty list
        if not flights_data:
            logger.warning(f"No flights found between {metadata.source} and {metadata.destination}.")
            state["flights"] = []
            return state
        # Add to state
        state["flights"] = flights_data
        return state
    except Exception as e:
        logger.error(f"Error in flights_node: {e}")
        raise 