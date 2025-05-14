import asyncio
import os
from dotenv import load_dotenv
from app.nodes.agents.hotel_node import hotel_node
from app.schemas.trip_schema import TripMetadata
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_hotel_node():
    """Test the hotel node functionality."""
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
            preferences=["luxury"]  # Test with luxury preference
        )
        
        # Create initial state
        state = {
            "metadata": metadata,
            "error": None
        }
        
        # Test hotel node
        logger.info("Testing hotel node...")
        result = await hotel_node(state)
        
        # Check results
        if "error" in result and result["error"]:
            logger.error(f"Error in hotel node: {result['error']}")
            return
            
        hotel = result.get("hotel")
        if not hotel:
            logger.error("No hotel found in result")
            return
            
        # Log hotel details
        logger.info("\nHotel Details:")
        logger.info(f"Name: {hotel.get('name')}")
        logger.info(f"Rating: {hotel.get('rating')}")
        logger.info(f"Price per night: ${hotel.get('price_per_night')}")
        logger.info(f"Location: {hotel.get('location')}")
        logger.info(f"Amenities: {', '.join(hotel.get('amenities', []))}")
        
        # Verify required fields
        required_fields = ['name', 'rating', 'price_per_night', 'location', 'amenities', 'place_id']
        missing_fields = [field for field in required_fields if field not in hotel]
        
        if missing_fields:
            logger.error(f"Missing required fields: {missing_fields}")
        else:
            logger.info("All required fields present")
            
        # Verify price level matches preferences
        if "luxury" in metadata.preferences:
            expected_price_level = 4  # Luxury hotels should be price level 4
            if hotel.get('price_per_night', 0) < 300:  # Luxury hotels typically cost more
                logger.warning("Hotel price seems low for luxury preference")
        
        logger.info("Hotel node test completed successfully")
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_hotel_node()) 