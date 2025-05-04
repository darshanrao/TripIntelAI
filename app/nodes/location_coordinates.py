import os
import requests
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

# Load environment variables
load_dotenv()

class LocationCoordinates:
    """Class to handle OpenCage API integration for getting location coordinates."""
    
    def __init__(self):
        self.api_key = os.getenv('OPENCAGE_API_KEY')
        if not self.api_key:
            raise ValueError("OPENCAGE_API_KEY environment variable not set")
        self.base_url = "https://api.opencagedata.com/geocode/v1/json"
        self.llm = ChatAnthropic(
            model="claude-3-sonnet-20240229",
            temperature=0.2,
            max_tokens=4000
        )
    
    async def get_proper_address(self, place_name: str) -> Optional[str]:
        """
        Use Claude to generate a proper address for a place that will work with the OpenCage API.
        The function will try to include city, state, and country information to improve geocoding accuracy.
        
        Args:
            place_name: Name of the place to get address for
            
        Returns:
            Properly formatted address string or None if address couldn't be generated
        """
        prompt = f"""
        Given the following place name, generate a complete address that would work well with the OpenCage geocoding service.
        The address should follow this format: "place name, city, state/province, country" where:
        - Place name is the original name or a well-known alternative
        - City is the main city where the place is located
        - State/province is the full name (not code)
        - Country is the full country name
        
        For example:
        - "Rockefeller Center" -> "Rockefeller Center, New York, New York, United States"
        - "Eiffel Tower" -> "Eiffel Tower, Paris, Île-de-France, France"
        - "Sydney Opera House" -> "Sydney Opera House, Sydney, New South Wales, Australia"
        
        Important:
        1. Always include the country name
        2. Use full state/province names, not codes
        3. Use well-known city names
        4. Keep the original place name if it's a landmark
        5. Return ONLY the address string, nothing else
        
        Place name: {place_name}
        """
        
        try:
            response = await self.llm.ainvoke(
                [HumanMessage(content=prompt)]
            )
            address = response.content.strip()
            
            # Validate the address format
            if not address or len(address.split(',')) < 2:
                print(f"Generated address is incomplete: {address}")
                return None
                
            print(f"Generated proper address: {address}")
            return address
            
        except Exception as e:
            print(f"Error generating address for {place_name}: {str(e)}")
            return None
    
    async def get_coordinates(self, place_name: str, state_code: str = "", country_code: str = "US", limit: int = 1) -> Optional[Dict[str, float]]:
        """
        Get latitude and longitude coordinates for a place using OpenCage API.
        If initial lookup fails, uses Claude to generate a proper address and tries again.
        
        Args:
            place_name: Name of the place to search for
            state_code: State code (optional)
            country_code: Country code (default: "US")
            limit: Maximum number of results to return (default: 1)
            
        Returns:
            Dictionary with 'lat' and 'lon' keys if successful, None otherwise
        """
        try:
            # First try with the original place name
            coords = self._get_coordinates_internal(place_name)
            if coords:
                return coords
            
            # If that fails, try with a proper address from Claude
            proper_address = await self.get_proper_address(place_name)
            if proper_address and proper_address != place_name:  # Only try if we got a different address
                print(f"Trying with proper address: {proper_address}")
                coords = self._get_coordinates_internal(proper_address)
                if coords:
                    return coords
            
            print(f"No coordinates found for place: {place_name}")
            return None
            
        except Exception as e:
            print(f"Error getting coordinates for {place_name}: {str(e)}")
            return None
    
    def _get_coordinates_internal(self, query: str) -> Optional[Dict[str, float]]:
        """
        Internal method to get coordinates from OpenCage API.
        
        Args:
            query: Query string to search for
            
        Returns:
            Dictionary with 'lat' and 'lon' keys if successful, None otherwise
        """
        try:
            # Make the API request
            params = {
                "q": query,
                "key": self.api_key,
                "limit": 1,
                "no_annotations": 1,
                "language": "en"
            }
            
            print(f"Making API request for: {query}")
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get("results"):
                print(f"No results found for query: {query}")
                return None
            
            # Return the first result's coordinates
            result = data["results"][0]["geometry"]
            coordinates = {
                "lat": result["lat"],
                "lon": result["lng"]
            }
            print(f"Found coordinates: {coordinates}")
            return coordinates
            
        except requests.exceptions.RequestException as e:
            print(f"API request failed for {query}: {str(e)}")
            return None
        except (KeyError, IndexError) as e:
            print(f"Error parsing API response for {query}: {str(e)}")
            return None
        except Exception as e:
            print(f"Unexpected error for {query}: {str(e)}")
            return None
    
    async def get_coordinates_for_places(self, places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Get coordinates for a list of places.
        
        Args:
            places: List of place dictionaries with at least a 'name' key
            
        Returns:
            List of places with added 'coordinates' key
        """
        places_with_coords = []
        
        for place in places:
            if "name" not in place:
                continue
                
            coords = await self.get_coordinates(place["name"])
            if coords:
                place["coordinates"] = coords
            places_with_coords.append(place)
        
        return places_with_coords 