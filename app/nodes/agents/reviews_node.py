from typing import Dict, Any, List
import os
import googlemaps
from app.utils.logger import logger

async def reviews_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get reviews for places and enhance place information.
    
    Args:
        state: Current state containing places information
        
    Returns:
        Updated state with enhanced place information including reviews
    """
    try:
        # Get places from state
        places = state.get("places", [])
        if not places:
            raise ValueError("No places found in state")
            
        # Initialize Google Maps client
        gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API_KEY"))
        
        # Get reviews for each place
        for place in places:
            place_id = place.get("place_id")
            if not place_id:
                continue
                
            # Get place details including reviews
            place_details = gmaps.place(place_id, fields=["reviews", "opening_hours", "price_level"])
            
            # Process reviews
            reviews = place_details.get("result", {}).get("reviews", [])
            processed_reviews = []
            
            for review in reviews:
                processed_review = {
                    "rating": review.get("rating"),
                    "text": review.get("text"),
                    "time": review.get("time"),
                    "author": review.get("author_name")
                }
                processed_reviews.append(processed_review)
            
            # Enhance place information
            place.update({
                "reviews": processed_reviews,
                "opening_hours": place_details.get("result", {}).get("opening_hours", {}).get("weekday_text", []),
                "price_level": place_details.get("result", {}).get("price_level")
            })
        
        # Update state with enhanced places
        state["places"] = places
        
        return state
        
    except Exception as e:
        logger.error(f"Error in reviews node: {str(e)}")
        state["error"] = str(e)
        return state 