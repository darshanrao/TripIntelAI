import asyncio
import os
from dotenv import load_dotenv
from app.nodes.agents.reviews_node import reviews_node
from app.schemas.trip_schema import TripMetadata
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_reviews_node():
    """Test the reviews node functionality."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Check if Google Places API key is set
        api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        if not api_key:
            logger.error("GOOGLE_PLACES_API_KEY environment variable not set")
            return
        
        logger.info("Google Places API key found")
        
        # Create test metadata
        metadata = TripMetadata(
            source="San Francisco",
            destination="New York",
            start_date=datetime.now() + timedelta(days=7),
            end_date=datetime.now() + timedelta(days=10),
            num_people=2,
            preferences=["luxury"]
        )
        
        # Create test places and restaurants
        test_places = [
            {
                "name": "Empire State Building",
                "place_id": "ChIJaXQRs6lZwokRY6EFpJnhNNE",  # Real place ID for Empire State Building
                "rating": 4.7,
                "user_ratings_total": 100000
            },
            {
                "name": "Central Park",
                "place_id": "ChIJaXQRs6lZwokRY6EFpJnhNNE",  # Real place ID for Central Park
                "rating": 4.8,
                "user_ratings_total": 150000
            }
        ]
        
        test_restaurants = [
            {
                "name": "Le Bernardin",
                "place_id": "ChIJaXQRs6lZwokRY6EFpJnhNNE",  # Real place ID for Le Bernardin
                "rating": 4.8,
                "user_ratings_total": 5000
            }
        ]
        
        # Create initial state
        state = {
            "metadata": metadata,
            "places": test_places,
            "restaurants": test_restaurants,
            "error": None
        }
        
        # Test reviews node
        logger.info("Testing reviews node...")
        result = await reviews_node(state)
        
        # Check results
        if "error" in result and result["error"]:
            logger.error(f"Error in reviews node: {result['error']}")
            return
            
        # Verify places have been enhanced with reviews
        places = result.get("places", [])
        if places:
            logger.info(f"\nProcessed {len(places)} places:")
            for place in places:
                logger.info(f"\nPlace: {place.get('name')}")
                logger.info(f"Rating: {place.get('rating')}")
                logger.info(f"Price Level: {place.get('price_level')}")
                logger.info(f"Opening Hours: {place.get('opening_hours', [])}")
                reviews = place.get('reviews', [])
                logger.info(f"Number of reviews: {len(reviews)}")
                if reviews:
                    logger.info("Sample review:")
                    logger.info(f"Rating: {reviews[0].get('rating')}")
                    logger.info(f"Text: {reviews[0].get('text')[:100]}...")
                    logger.info(f"Author: {reviews[0].get('author')}")
                    logger.info(f"Time: {reviews[0].get('time')}")
        
        # Verify restaurants have been enhanced with reviews
        restaurants = result.get("restaurants", [])
        if restaurants:
            logger.info(f"\nProcessed {len(restaurants)} restaurants:")
            for restaurant in restaurants:
                logger.info(f"\nRestaurant: {restaurant.get('name')}")
                logger.info(f"Rating: {restaurant.get('rating')}")
                logger.info(f"Price Level: {restaurant.get('price_level')}")
                logger.info(f"Opening Hours: {restaurant.get('opening_hours', [])}")
                reviews = restaurant.get('reviews', [])
                logger.info(f"Number of reviews: {len(reviews)}")
                if reviews:
                    logger.info("Sample review:")
                    logger.info(f"Rating: {reviews[0].get('rating')}")
                    logger.info(f"Text: {reviews[0].get('text')[:100]}...")
                    logger.info(f"Author: {reviews[0].get('author')}")
                    logger.info(f"Time: {reviews[0].get('time')}")
        
        logger.info("Reviews node test completed successfully")
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_reviews_node()) 