from typing import Dict, Any
import os
import random
from datetime import datetime, timedelta
from app.schemas.trip_schema import Hotel, TripMetadata
from app.nodes.agent_nodes import (
    get_gmaps_client,
    geocode_location,
    _find_hotels,
    _select_best_hotel,
    _get_default_amenities,
    _estimate_price,
    _fallback_hotel_to_mock
)

async def hotel_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Find and select a hotel based on user preferences and location."""
    try:
        metadata = state.get("metadata")
        if not metadata:
            raise ValueError("No metadata found in state")
        
        # Get destination coordinates
        gmaps = get_gmaps_client()
        lat, lng = geocode_location(metadata.destination, gmaps)
        
        if not lat or not lng:
            raise ValueError(f"Could not geocode location: {metadata.destination}")
        
        # Search for hotels
        hotels = _find_hotels(lat, lng)
        
        if not hotels:
            # Fallback to mock data if no hotels found
            return await _fallback_hotel_to_mock(state, metadata)
        
        # Select best hotel based on preferences
        best_hotel = _select_best_hotel(hotels, metadata.preferences)
        
        if not best_hotel:
            # Fallback to mock data if no suitable hotel found
            return await _fallback_hotel_to_mock(state, metadata)
        
        # Get hotel details
        hotel_details = gmaps.place(best_hotel["place_id"], fields=["name", "rating", "formatted_address", "price_level"])
        
        # Create hotel object
        hotel = Hotel(
            name=hotel_details["result"]["name"],
            rating=hotel_details["result"].get("rating", 0),
            price_per_night=_estimate_price(
                hotel_details["result"].get("price_level", 2),
                metadata.preferences
            ),
            location=hotel_details["result"]["formatted_address"],
            amenities=_get_default_amenities(hotel_details["result"].get("price_level", 2)),
            place_id=best_hotel["place_id"]
        )
        
        # Add to state
        state["hotel"] = hotel.dict()
        
        return state
        
    except Exception as e:
        print(f"Error in hotel_node: {e}")
        # Fallback to mock data on error
        return await _fallback_hotel_to_mock(state, metadata) 