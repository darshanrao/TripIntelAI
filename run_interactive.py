import uvicorn
import os
import sys
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
load_dotenv()

# Ensure required API keys are set
required_keys = ["ANTHROPIC_API_KEY", "GOOGLE_PLACES_API_KEY"]
missing_keys = [key for key in required_keys if not os.getenv(key)]

if missing_keys:
    logger.error(f"The following environment variables are required: {', '.join(missing_keys)}")
    logger.error("Please set them in a .env file or in your environment.")
    exit(1)

if __name__ == "__main__":
    print("=" * 80)
    print("Starting AI Travel Planner API (Interactive Version) on port 8002...")
    print("This version uses an interactive trip validator that will ask follow-up questions")
    print("when trip information is incomplete.")
    print("-" * 80)
    print("API Documentation: http://localhost:8002/docs")
    print("=" * 80)
    
    # Run the API server
    uvicorn.run("app.main_interactive:app", host="0.0.0.0", port=8002, reload=True) 