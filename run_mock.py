import uvicorn
import os
import sys
import logging
import traceback
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the mock implementation
from app.graph.trip_planner_graph_mock import TripPlannerGraphMock
from app.schemas.trip_schema import TripData

# Load environment variables from .env file
load_dotenv()

# Create FastAPI app
app = FastAPI(title="AI Travel Planner (Mock Implementation)")

# Initialize the mock trip planner
trip_planner = TripPlannerGraphMock()

class ChatRequest(BaseModel):
    """Request model for chat-based interactions."""
    query: str

class ChatResponse(BaseModel):
    """Response model for chat-based interactions."""
    itinerary: Optional[str] = None
    error: Optional[str] = None
    is_valid: Optional[bool] = None
    validation_errors: Optional[list] = None

@app.post("/chat", response_model=ChatResponse)
async def chat_query(request: ChatRequest):
    """
    Process a natural language query through the travel planning pipeline.
    
    Example:
    ```
    {"query": "I want to plan a trip from Boston to NYC from May 15 to May 18, 2025 for 2 people."}
    ```
    """
    logger.info(f"Received chat request: {request.query}")
    try:
        result = await trip_planner.process(request.query)
        logger.info(f"Processed request: is_valid={result.get('is_valid', False)}")
        
        # Handle validation errors
        if not result.get("is_valid", True):
            logger.warning(f"Validation failed: {result.get('validation_errors', [])}")
            return ChatResponse(
                error="Invalid trip parameters",
                is_valid=False,
                validation_errors=result.get("validation_errors", ["Unknown validation error"])
            )
        
        # Check if itinerary was generated
        if not result.get("itinerary"):
            logger.warning("No itinerary generated")
            return ChatResponse(
                error="Failed to generate itinerary",
                is_valid=True
            )
        
        return ChatResponse(
            itinerary=result.get("itinerary"),
            is_valid=True
        )
    except Exception as e:
        # Log the full exception traceback
        logger.error(f"Error processing request: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {
        "message": "Welcome to AI Travel Planner API (Mock Implementation)",
        "endpoints": {
            "/chat": "For natural language queries",
        }
    }

if __name__ == "__main__":
    print("Starting AI Travel Planner API (Mock Implementation) on port 8001...")
    uvicorn.run("run_mock:app", host="0.0.0.0", port=8001, reload=True) 