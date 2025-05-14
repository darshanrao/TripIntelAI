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
        restaurants = state.get("restaurants", [])
        
        if not places and not restaurants:
            logger.warning("No places or restaurants found in state for review processing")
            return state
            
        # Check if the Google Places API key is loaded
        api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        if not api_key:
            logger.error("Google Places API key not found. Cannot initialize Google Maps client.")
            raise ValueError("Google Places API key not found")
        else:
            logger.info("Google Places API key loaded successfully.")
        
        # Initialize Google Maps client
        gmaps = googlemaps.Client(key=api_key)
        
        # Process places
        if places:
            logger.info(f"Processing reviews for {len(places)} places")
            for place in places:
                place_id = place.get("place_id")
                if not place_id:
                    continue
                    
                try:
                    # Get place details including reviews, opening hours, and rating
                    place_details = gmaps.place(
                        place_id,
                        fields=[
                            "reviews",
                            "opening_hours",
                            "rating",
                            "user_ratings_total",
                            "formatted_address"
                        ]
                    )
                    
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
                    result = place_details.get("result", {})
                    place.update({
                        "reviews": processed_reviews,
                        "opening_hours": result.get("opening_hours", {}).get("weekday_text", []),
                        "rating": result.get("rating", place.get("rating")),
                        "user_ratings_total": result.get("user_ratings_total", place.get("user_ratings_total")),
                        "formatted_address": result.get("formatted_address", place.get("formatted_address"))
                    })
                except Exception as e:
                    logger.error(f"Error processing reviews for place {place.get('name')}: {str(e)}")
                    continue
        
        # Process restaurants
        if restaurants:
            logger.info(f"Processing reviews for {len(restaurants)} restaurants")
            for restaurant in restaurants:
                place_id = restaurant.get("place_id")
                if not place_id:
                    continue
                    
                try:
                    # Get restaurant details including reviews, opening hours, and rating
                    restaurant_details = gmaps.place(
                        place_id,
                        fields=[
                            "reviews",
                            "opening_hours",
                            "rating",
                            "user_ratings_total",
                            "formatted_address"
                        ]
                    )
                    
                    # Process reviews
                    reviews = restaurant_details.get("result", {}).get("reviews", [])
                    processed_reviews = []
                    
                    for review in reviews:
                        processed_review = {
                            "rating": review.get("rating"),
                            "text": review.get("text"),
                            "time": review.get("time"),
                            "author": review.get("author_name")
                        }
                        processed_reviews.append(processed_review)
                    
                    # Enhance restaurant information
                    result = restaurant_details.get("result", {})
                    restaurant.update({
                        "reviews": processed_reviews,
                        "opening_hours": result.get("opening_hours", {}).get("weekday_text", []),
                        "rating": result.get("rating", restaurant.get("rating")),
                        "user_ratings_total": result.get("user_ratings_total", restaurant.get("user_ratings_total")),
                        "formatted_address": result.get("formatted_address", restaurant.get("formatted_address"))
                    })
                except Exception as e:
                    logger.error(f"Error processing reviews for restaurant {restaurant.get('name')}: {str(e)}")
                    continue
        
        # Update state with enhanced places and restaurants
        state["places"] = places
        state["restaurants"] = restaurants
        
        return state
        
    except Exception as e:
        logger.error(f"Error in reviews node: {str(e)}")
        state["error"] = str(e)
        return state 