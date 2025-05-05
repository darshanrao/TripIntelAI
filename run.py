import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Ensure required API keys are set
required_keys = ["ANTHROPIC_API_KEY", "GOOGLE_PLACES_API_KEY"]
missing_keys = [key for key in required_keys if not os.getenv(key)]

if missing_keys:
    print(f"Error: The following environment variables are required: {', '.join(missing_keys)}")
    print("Please set them in a .env file or in your environment.")
    exit(1)

if __name__ == "__main__":
    print("Starting AI Travel Planner API...")
    
    # Use environment variable to control reload mode
    is_dev = os.getenv("DEV_MODE", "False").lower() == "true"
    
    if is_dev:
        print("- Running in development mode with hot reload enabled")
        uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
    else:
        print("- Running in production mode (no hot reload)")
        uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False) 