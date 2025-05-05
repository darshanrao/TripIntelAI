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
    
    # Get environment mode and port
    dev_mode = os.getenv("DEV_MODE", "False").lower() in ("true", "1", "t")
    port = int(os.getenv("PORT", "8000"))
    
    if dev_mode:
        print(f"- Running in DEVELOPMENT mode with hot reload on port {port}")
        uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
    else:
        print(f"- Running in PRODUCTION mode on port {port}")
        # In production mode, never use reload
        uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False) 