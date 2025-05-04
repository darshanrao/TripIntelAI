from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel
from app.graph.trip_planner_graph import TripPlannerGraph
from app.schemas.trip_schema import TripData
from typing import Optional, List, Dict, Any
import tempfile
import os
import shutil
import uuid
from endpoints.services.llm_service import parse_user_input
from endpoints.services.speech_to_text import transcribe_audio
from fastapi.middleware.cors import CORSMiddleware

# Import our interactive validator
from app.nodes.interactive_trip_validator_node import interactive_trip_validator_node, process_user_response
from app.nodes.chat_input_node import chat_input_node
from mock_intent_parser import mock_intent_parser

app = FastAPI(title="AI Travel Planner (Interactive)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the graph
trip_planner = TripPlannerGraph()

# Dictionary to store conversation states
conversation_states = {}

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
    next_question: Optional[str] = None
    interactive_mode: Optional[bool] = None

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
    Provides an interactive experience by asking follow-up questions if needed.
    
    Example:
    ```
    {"query": "I want to plan a trip from Boston to NYC from May 15 to May 18, 2025 for 2 people."}
    ```
    """
    try:
        # Check if conversation exists
        if request.conversation_id and request.conversation_id in conversation_states:
            # Get existing state
            state = conversation_states[request.conversation_id]
            
            # Check if we're in interactive mode
            if state.get("interactive_mode") and state.get("missing_fields"):
                # Process the user response to a previous question
                state = await process_user_response(state, request.query)
                
                # Save the updated state
                conversation_states[request.conversation_id] = state
                
                # If we're still in interactive mode, return the next question
                if state.get("interactive_mode") and state.get("next_question"):
                    return ChatResponse(
                        conversation_id=request.conversation_id,
                        interactive_mode=True,
                        next_question=state["next_question"]
                    )
                
                # If validation is now complete, continue with processing
                if state.get("is_valid"):
                    result = await trip_planner.process_with_state(state)
                    
                    # Clean up the conversation state
                    if request.conversation_id in conversation_states:
                        del conversation_states[request.conversation_id]
                    
                    return ChatResponse(
                        itinerary=result.get("itinerary"),
                        is_valid=True,
                        conversation_id=request.conversation_id,
                        suggestions=result.get("next_suggestions", [])
                    )
            
            # Not in interactive mode but has a valid conversation - handle as a new query
            # Reset the state for a new query in the same conversation
            state = {"query": request.query}
        else:
            # New conversation
            conversation_id = request.conversation_id or str(uuid.uuid4())
            state = {"query": request.query}
            request.conversation_id = conversation_id
        
        # Begin processing the query
        state = await chat_input_node(state)
        state = await mock_intent_parser(state)
        
        # Check if we need to validate
        state = await interactive_trip_validator_node(state)
        
        # If we need more information, enter interactive mode
        if not state.get("is_valid", False) and state.get("interactive_mode") and state.get("next_question"):
            # Save the state for future interactions
            conversation_states[request.conversation_id] = state
            
            # Return the question for the missing field
            return ChatResponse(
                conversation_id=request.conversation_id,
                interactive_mode=True,
                next_question=state["next_question"],
                is_valid=False
            )
        
        # If validation succeeded, proceed with the pipeline
        if state.get("is_valid", False):
            result = await trip_planner.process_with_state(state)
            
            return ChatResponse(
                itinerary=result.get("itinerary"),
                is_valid=True,
                conversation_id=request.conversation_id,
                suggestions=result.get("next_suggestions", [])
            )
        
        # Handle validation errors (if not in interactive mode)
        return ChatResponse(
            error="Invalid trip parameters",
            is_valid=False,
            validation_errors=state.get("validation_errors", ["Unknown validation error"]),
            conversation_id=request.conversation_id,
            suggestions=["Try specifying dates in MM/DD/YYYY format", 
                        "Make sure to include your destination",
                        "Specify the number of travelers"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversations")
async def list_conversations():
    """List all active conversation IDs."""
    return {"conversations": list(conversation_states.keys())}

@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation state."""
    if conversation_id in conversation_states:
        del conversation_states[conversation_id]
        return {"message": f"Conversation {conversation_id} deleted"}
    raise HTTPException(status_code=404, detail="Conversation not found")

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
        "message": "Welcome to AI Travel Planner API (Interactive Version)",
        "endpoints": {
            "/chat": "For natural language queries with interactive follow-up",
            "/generate-itinerary": "For structured trip data",
            "/conversations": "List all active conversations",
            "/conversations/{conversation_id}": "Delete a conversation",
        }
    }

@app.post("/conversations")
async def create_conversation():
    """Create a new conversation and return the conversation ID."""
    try:
        conversation_id = str(uuid.uuid4())
        return {"conversation_id": conversation_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversations/{conversation_id}", response_model=List[ChatMessageHistory])
async def get_conversation_history(conversation_id: str):
    """Get message history for a specific conversation."""
    try:
        # Mock implementation - would fetch from database in production
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

if __name__ == "__main__":
    import uvicorn
    print("Starting AI Travel Planner API (Interactive Version) on port 8002...")
    uvicorn.run("app.main_interactive:app", host="0.0.0.0", port=8002, reload=True) 