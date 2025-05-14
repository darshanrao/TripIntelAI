import asyncio
import os
from dotenv import load_dotenv
import logging
from app.nodes.agents.places_node import fetch_attractions, fetch_restaurants
from app.schemas.trip_schema import TripMetadata
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def test_places_api():
    # Create test metadata
    metadata = TripMetadata(
        source="San Francisco",
        destination="New York",
        start_date=datetime(2024, 5, 20),
        end_date=datetime(2024, 5, 25),
        num_people=2,
        preferences=["museums", "restaurants"]
    )
    
    # Create initial state
    state = {
        "metadata": metadata
    }
    
    # Test fetch_attractions
    logger.info("Testing fetch_attractions...")
    try:
        attractions_state = await fetch_attractions(state)
        attractions = attractions_state.get("attractions", [])
        logger.info(f"Found {len(attractions)} attractions")
        for i, attraction in enumerate(attractions[:3], 1):  # Show first 3 attractions
            logger.info(f"\nAttraction {i}:")
            logger.info(f"Name: {attraction.get('name')}")
            logger.info(f"Rating: {attraction.get('rating')}")
            logger.info(f"Types: {attraction.get('types')}")
    except Exception as e:
        logger.error(f"Error testing fetch_attractions: {e}")
    
    # Test fetch_restaurants
    logger.info("\nTesting fetch_restaurants...")
    try:
        restaurants_state = await fetch_restaurants(state)
        restaurants = restaurants_state.get("restaurants", [])
        logger.info(f"Found {len(restaurants)} restaurants")
        for i, restaurant in enumerate(restaurants[:3], 1):  # Show first 3 restaurants
            logger.info(f"\nRestaurant {i}:")
            logger.info(f"Name: {restaurant.get('name')}")
            logger.info(f"Rating: {restaurant.get('rating')}")
            logger.info(f"Types: {restaurant.get('types')}")
    except Exception as e:
        logger.error(f"Error testing fetch_restaurants: {e}")

if __name__ == "__main__":
    # Check if Google Places API key is set
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
        logger.error("GOOGLE_PLACES_API_KEY environment variable not set")
    else:
        logger.info("Google Places API key found, running tests...")
        asyncio.run(test_places_api()) 