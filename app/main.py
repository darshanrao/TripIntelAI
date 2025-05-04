from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel
from app.graph.trip_planner_graph import TripPlannerGraph
from app.schemas.trip_schema import TripData
from typing import Optional, List, Dict, Any
import tempfile
import os
import shutil
from endpoints.services.llm_service import parse_user_input
from endpoints.services.speech_to_text import transcribe_audio
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI Travel Planner")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the graph
trip_planner = TripPlannerGraph()

class ChatRequest(BaseModel):
    """Request model for chat-based interactions."""
    query: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    """Response model for chat-based interactions."""
    itinerary: Optional[str] = None
    error: Optional[str] = None
    is_valid: Optional[bool] = None
    validation_errors: Optional[list] = None
    conversation_id: Optional[str] = None
    suggestions: Optional[List[str]] = None

class ChatMessageHistory(BaseModel):
    """Model for chat message history."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str

class SavedTrip(BaseModel):
    """Model for saved trips."""
    trip_id: str
    user_id: Optional[str] = None
    trip_data: TripData
    created_at: str
    updated_at: Optional[str] = None
    name: Optional[str] = None

class AnalyzeInputRequest(BaseModel):
    input: str

@app.post("/chat", response_model=ChatResponse)
async def chat_query(request: ChatRequest):
    """
    Process a natural language query through the travel planning pipeline.
    
    Example:
    ```
    {"query": "I want to plan a trip from Boston to NYC from May 15 to May 18, 2025 for 2 people."}
    ```
    """
    try:
        result = await trip_planner.process(request.query)
        
        # Handle validation errors
        if not result.get("is_valid", True):
            return ChatResponse(
                error="Invalid trip parameters",
                is_valid=False,
                validation_errors=result.get("validation_errors", ["Unknown validation error"]),
                conversation_id=request.conversation_id,
                suggestions=["Try specifying dates in MM/DD/YYYY format", 
                             "Make sure to include your destination",
                             "Specify the number of travelers"]
            )
        
        return ChatResponse(
            itinerary=result.get("itinerary"),
            is_valid=True,
            conversation_id=request.conversation_id,
            suggestions=result.get("next_suggestions", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-itinerary")
async def generate_itinerary(trip_data: TripData):
    """
    Generate a travel itinerary based on structured trip data.
    This endpoint is for direct API calls with structured data.
    """
    try:
        result = await trip_planner.process_with_trip_data(trip_data)
        return {"itinerary": result.get("itinerary")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {
        "message": "Welcome to AI Travel Planner API",
        "endpoints": {
            "/chat": "For natural language queries",
            "/generate-itinerary": "For structured trip data",
            "/conversations/{conversation_id}": "Get chat history",
            "/trips": "Get saved trips",
            "/trips/{trip_id}": "Get specific trip details"
        }
    }

@app.post("/conversations")
async def create_conversation():
    """Create a new conversation and return the conversation ID."""
    try:
        # In a real implementation, you would generate a unique ID and store in database
        import uuid
        conversation_id = str(uuid.uuid4())
        return {"conversation_id": conversation_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversations/{conversation_id}", response_model=List[ChatMessageHistory])
async def get_conversation_history(conversation_id: str):
    """Get message history for a specific conversation."""
    try:
        # Mock implementation - would fetch from database in production
        # Return mock data for now
        return [
            {
                "role": "user",
                "content": "I want to plan a trip to Paris",
                "timestamp": "2023-07-15T10:30:00Z"
            },
            {
                "role": "assistant",
                "content": "Great! When would you like to go to Paris and for how many people?",
                "timestamp": "2023-07-15T10:30:05Z"
            }
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trips", response_model=SavedTrip)
async def save_trip(trip_data: TripData, name: Optional[str] = None, user_id: Optional[str] = None):
    """Save a trip plan."""
    try:
        import uuid
        from datetime import datetime
        
        trip_id = str(uuid.uuid4())
        current_time = datetime.now().isoformat()
        
        saved_trip = {
            "trip_id": trip_id,
            "user_id": user_id,
            "trip_data": trip_data,
            "created_at": current_time,
            "name": name or f"Trip to {trip_data.metadata.destination}"
        }
        
        # In production: save to database here
        
        return saved_trip
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trips", response_model=List[SavedTrip])
async def get_saved_trips(user_id: Optional[str] = None):
    """Get all saved trips, optionally filtered by user ID."""
    try:
        # Mock implementation - would fetch from database in production
        return []  # Empty list for now
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trips/{trip_id}", response_model=SavedTrip)
async def get_trip(trip_id: str):
    """Get details for a specific saved trip."""
    try:
        # Mock implementation - would fetch from database in production
        raise HTTPException(status_code=404, detail="Trip not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search", response_model=Dict[str, Any])
async def search_travel_options(
    destination: str,
    start_date: str,
    end_date: str,
    num_people: int = 1,
    preferences: Optional[List[str]] = None
):
    """Search for travel options matching the given criteria."""
    try:
        # Mock implementation - would call external services in production
        return {
            "flights": [],
            "hotels": [],
            "activities": []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-input")
async def analyze_input(request: AnalyzeInputRequest):
    try:
        llm_response = parse_user_input(request.input)
        return {"response": llm_response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/voice-input")
async def voice_input(file: UploadFile = File(...)):
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp:
            shutil.copyfileobj(file.file, temp)
            temp_path = temp.name
        transcript = transcribe_audio(temp_path)
        llm_response = parse_user_input(transcript)
        return {"response": llm_response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path) 