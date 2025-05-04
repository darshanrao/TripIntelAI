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
import subprocess
import time
from pathlib import Path

# Import our consolidated validator
from app.nodes.trip_validator_node import trip_validator_node, process_user_response
from app.nodes.chat_input_node import chat_input_node
from app.nodes.intent_parser_node import intent_parser_node
# Add missing node imports
from app.nodes.planner_node import planner_node
from app.nodes.agent_nodes import flights_node, places_node, restaurants_node, hotel_node, budget_node, reviews_node, route_node
from app.nodes.summary_node import summary_node

# Import our flight booking router
from app.api.flight_booking import router as flight_booking_router

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

# Dictionary to store conversation states
conversation_states = {}

# Create a dedicated audio directory
AUDIO_DIR = Path("audio_files")
AUDIO_DIR.mkdir(exist_ok=True)

# Include the flight booking router
app.include_router(flight_booking_router)

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
        state = await intent_parser_node(state)
        
        # Check if we need to validate with interactive mode
        state["interactive_mode"] = True  # Enable interactive mode
        state = await trip_validator_node(state)
        
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
        "message": "Welcome to AI Travel Planner API",
        "endpoints": {
            "/chat": "For natural language queries with interactive follow-up",
            "/generate-itinerary": "For structured trip data",
            "/conversations": "List all active conversations",
            "/conversations/{conversation_id}": "Get or delete a conversation",
            "/trips": "Get saved trips",
            "/trips/{trip_id}": "Get specific trip details"
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
        # Check if we have an active conversation with this ID
        if conversation_id in conversation_states and "conversation_history" in conversation_states[conversation_id]:
            # Return actual conversation history
            return conversation_states[conversation_id]["conversation_history"]
        
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
        try:
            # MODIFIED: Process input using the CLI-style approach instead of directly calling trip_planner.process
            # Initial state (same as CLI version)
            state = {"query": request.input}
            
            # Step 1: Chat Input Node
            print("[DEBUG] Processing with chat_input_node")
            state = await chat_input_node(state)
            
            # Step 2: Intent Parser Node
            print("[DEBUG] Processing with intent_parser_node")
            state = await intent_parser_node(state)
            
            # Check for errors in intent parsing
            if "error" in state and state["error"]:
                print(f"[ERROR] Intent parser error: {state['error']}")
                return {
                    "success": False,
                    "response": f"Failed to understand your travel query: {state['error']}",
                    "error": state["error"]
                }
            
            # Check if metadata was extracted
            if "metadata" not in state or not state["metadata"]:
                print("[ERROR] No metadata extracted from query")
                return {
                    "success": False,
                    "response": "Could not extract travel details from your query",
                    "error": "No metadata was extracted"
                }
            
            # Step 3: Trip Validator Node
            print("[DEBUG] Processing with trip_validator_node")
            state = await trip_validator_node(state)
            
            # Check if trip is valid
            if not state.get('is_valid', False):
                return {
                    "success": False,
                    "response": "Your travel query couldn't be processed.",
                    "validation_errors": state.get("validation_errors", ["Unknown validation error"]),
                    "error": "Invalid trip parameters"
                }
            
            # Step 4: Planner Node
            print("[DEBUG] Processing with planner_node")
            state = await planner_node(state)
            
            # Step 5: Agent Nodes
            nodes_to_call = state.get('nodes_to_call', [])
            print(f"[DEBUG] Nodes to call: {nodes_to_call}")
            
            if 'flights' in nodes_to_call:
                print("[DEBUG] Processing with flights_node")
                state = await flights_node(state)
            
            if 'route' in nodes_to_call:
                print("[DEBUG] Processing with route_node")
                state = await route_node(state)
            
            if 'places' in nodes_to_call:
                print("[DEBUG] Processing with places_node")
                state = await places_node(state)
            
            if 'restaurants' in nodes_to_call:
                print("[DEBUG] Processing with restaurants_node")
                state = await restaurants_node(state)
            
            if 'hotel' in nodes_to_call:
                print("[DEBUG] Processing with hotel_node")
                state = await hotel_node(state)
            
            if 'budget' in nodes_to_call:
                print("[DEBUG] Processing with budget_node")
                state = await budget_node(state)
            
            # Step 6: Reviews Node
            print("[DEBUG] Processing with reviews_node")
            state = await reviews_node(state)
            
            # Step 7: Summary Node
            print("[DEBUG] Processing with summary_node")
            state = await summary_node(state)
            
            # Use the result from the state
            result = state
            print(f"[DEBUG] Final state keys: {result.keys()}")
            
            # Check if there was an error in processing
            if "error" in result and result["error"]:
                print(f"[ERROR] Trip planner error: {result['error']}")
                return {
                    "success": False,
                    "response": result.get("response", "I had trouble planning your trip based on that request."),
                    "error": result["error"]
                }
            
            # Extract a simple text response from the complex result
            response_text = ""
            structured_response = {}
            
            if isinstance(result, dict):
                # If we have an itinerary and daily_itinerary, return the structured data
                if "daily_itinerary" in result:
                    print("[DEBUG] Returning structured daily itinerary")
                    return {
                        "success": True,
                        "response": {
                            "trip_summary": result.get("trip_summary", {}),
                            "daily_itinerary": result.get("daily_itinerary", {}),
                            "review_highlights": result.get("review_highlights", {})
                        }
                    }
                # If we have just a trip_summary
                elif "trip_summary" in result:
                    print("[DEBUG] Returning trip_summary")
                    summary = result["trip_summary"]
                    response_text = f"Trip to {summary.get('destination', 'your destination')} planned for {summary.get('start_date', 'your dates')}"
                    structured_response = {
                        "trip_summary": summary
                    }
                # If we have a string itinerary
                elif "itinerary" in result and result["itinerary"]:
                    print("[DEBUG] Returning itinerary as string or object")
                    if isinstance(result["itinerary"], str):
                        response_text = result["itinerary"]
                    else:
                        # If itinerary is a dict with daily_itinerary
                        if isinstance(result["itinerary"], dict) and "daily_itinerary" in result["itinerary"]:
                            return {
                                "success": True,
                                "response": result["itinerary"]
                            }
                        response_text = f"Generated itinerary for your trip to {result.get('metadata', {}).get('destination', 'your destination')}"
                        structured_response = result["itinerary"]
                else:
                    response_text = "Your trip has been planned successfully."
            else:
                response_text = "Thank you for your query. Your trip is being processed."
            
            # Return either structured or simple response
            if structured_response:
                return {
                    "success": True,
                    "response": structured_response
                }
            else:
                return {
                    "success": True,
                    "response": response_text
                }
        except Exception as planning_error:
            print(f"[ERROR] Trip planning failed: {str(planning_error)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False, 
                "response": "I had trouble planning your trip. Could you try again with more details?",
                "error": str(planning_error)
            }
    except Exception as e:
        print(f"[ERROR] Request processing error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/voice-input")
async def voice_input(file: UploadFile = File(...), keep_debug_files: bool = False):
    temp_path = None
    try:
        # Get information about the file
        filename = file.filename
        content_type = file.content_type
        print(f"[DEBUG] Received file: {filename}, Content-Type: {content_type}")
        
        # Create temp file with the original extension to preserve format information
        original_ext = os.path.splitext(filename)[1] or ".mp3"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=original_ext) as temp:
            shutil.copyfileobj(file.file, temp)
            temp_path = temp.name
        
        print(f"[DEBUG] Saved uploaded file to {temp_path} (size: {os.path.getsize(temp_path)} bytes)")
        
        # Try transcribing the audio
        try:
            transcript = transcribe_audio(temp_path, keep_files=keep_debug_files)
            print(f"[DEBUG] Successfully transcribed: '{transcript}'")
            
            try:
                # MODIFIED: Process transcript using the CLI-style approach instead of directly calling trip_planner.process
                # Initial state (same as CLI version)
                state = {"query": transcript}
                
                # Step 1: Chat Input Node
                print("[DEBUG] Processing with chat_input_node")
                state = await chat_input_node(state)
                
                # Step 2: Intent Parser Node
                print("[DEBUG] Processing with intent_parser_node")
                state = await intent_parser_node(state)
                
                # Check for errors in intent parsing
                if "error" in state and state["error"]:
                    print(f"[ERROR] Intent parser error: {state['error']}")
                    return {
                        "success": False,
                        "transcript": transcript,
                        "response": f"Failed to understand your travel query: {state['error']}",
                        "error": state["error"]
                    }
                
                # Check if metadata was extracted
                if "metadata" not in state or not state["metadata"]:
                    print("[ERROR] No metadata extracted from query")
                    return {
                        "success": False,
                        "transcript": transcript,
                        "response": "Could not extract travel details from your query",
                        "error": "No metadata was extracted"
                    }
                
                # Step 3: Trip Validator Node
                print("[DEBUG] Processing with trip_validator_node")
                state = await trip_validator_node(state)
                
                # Check if trip is valid
                if not state.get('is_valid', False):
                    return {
                        "success": False,
                        "transcript": transcript,
                        "response": "Your travel query couldn't be processed.",
                        "validation_errors": state.get("validation_errors", ["Unknown validation error"]),
                        "error": "Invalid trip parameters"
                    }
                
                # Step 4: Planner Node
                print("[DEBUG] Processing with planner_node")
                state = await planner_node(state)
                
                # Step 5: Agent Nodes
                nodes_to_call = state.get('nodes_to_call', [])
                print(f"[DEBUG] Nodes to call: {nodes_to_call}")
                
                if 'flights' in nodes_to_call:
                    print("[DEBUG] Processing with flights_node")
                    state = await flights_node(state)
                
                if 'route' in nodes_to_call:
                    print("[DEBUG] Processing with route_node")
                    state = await route_node(state)
                
                if 'places' in nodes_to_call:
                    print("[DEBUG] Processing with places_node")
                    state = await places_node(state)
                
                if 'restaurants' in nodes_to_call:
                    print("[DEBUG] Processing with restaurants_node")
                    state = await restaurants_node(state)
                
                if 'hotel' in nodes_to_call:
                    print("[DEBUG] Processing with hotel_node")
                    state = await hotel_node(state)
                
                if 'budget' in nodes_to_call:
                    print("[DEBUG] Processing with budget_node")
                    state = await budget_node(state)
                
                # Step 6: Reviews Node
                print("[DEBUG] Processing with reviews_node")
                state = await reviews_node(state)
                
                # Step 7: Summary Node
                print("[DEBUG] Processing with summary_node")
                state = await summary_node(state)
                
                # Use the result from the state
                result = state
                print(f"[DEBUG] Final state keys: {result.keys()}")
                
                # Check if there was an error in processing
                if "error" in result and result["error"]:
                    print(f"[ERROR] Trip planner error: {result['error']}")
                    return {
                        "success": False,
                        "transcript": transcript,
                        "response": result.get("response", "I had trouble planning your trip based on that request."),
                        "error": result["error"]
                    }
                
                # Extract a simple text response from the complex result
                response_text = ""
                structured_response = {}
                
                if isinstance(result, dict):
                    # If we have an itinerary and daily_itinerary, return the structured data
                    if "daily_itinerary" in result:
                        print("[DEBUG] Returning structured daily itinerary")
                        return {
                            "success": True,
                            "transcript": transcript,
                            "response": {
                                "trip_summary": result.get("trip_summary", {}),
                                "daily_itinerary": result.get("daily_itinerary", {}),
                                "review_highlights": result.get("review_highlights", {})
                            }
                        }
                    # If we have just a trip_summary
                    elif "trip_summary" in result:
                        print("[DEBUG] Returning trip_summary")
                        summary = result["trip_summary"]
                        response_text = f"Trip to {summary.get('destination', 'your destination')} planned for {summary.get('start_date', 'your dates')}"
                        structured_response = {
                            "trip_summary": summary
                        }
                    # If we have a string itinerary
                    elif "itinerary" in result and result["itinerary"]:
                        print("[DEBUG] Returning itinerary as string or object")
                        if isinstance(result["itinerary"], str):
                            response_text = result["itinerary"]
                        else:
                            # If itinerary is a dict with daily_itinerary
                            if isinstance(result["itinerary"], dict) and "daily_itinerary" in result["itinerary"]:
                                return {
                                    "success": True,
                                    "transcript": transcript,
                                    "response": result["itinerary"]
                                }
                            response_text = f"Generated itinerary for your trip to {result.get('metadata', {}).get('destination', 'your destination')}"
                            structured_response = result["itinerary"]
                    else:
                        response_text = "Your trip has been planned successfully."
                else:
                    response_text = "Thank you for your query. Your trip is being processed."
                
                # Return either structured or simple response
                if structured_response:
                    return {
                        "success": True,
                        "transcript": transcript,
                        "response": structured_response
                    }
                else:
                    return {
                        "success": True,
                        "transcript": transcript,
                        "response": response_text
                    }
            except Exception as planning_error:
                print(f"[ERROR] Trip planning failed: {str(planning_error)}")
                import traceback
                traceback.print_exc()
                return {
                    "success": False,
                    "transcript": transcript,
                    "response": "I understood what you said, but had trouble planning your trip. Could you try again with more details?",
                    "error": str(planning_error)
                }
        except Exception as transcription_error:
            # Handle transcription errors more gracefully
            print(f"[ERROR] Transcription failed: {str(transcription_error)}")
            return {
                "response": "I'm having trouble understanding the audio. Could you please speak more clearly or try typing your message instead?",
                "error": str(transcription_error)
            }
    except Exception as e:
        print(f"[ERROR] Voice input processing error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up the temporary file if it still exists and we're not in debug mode
        if temp_path and os.path.exists(temp_path) and not keep_debug_files:
            os.remove(temp_path)
            print(f"[DEBUG] Deleted temporary file: {temp_path}")
        elif temp_path and os.path.exists(temp_path) and keep_debug_files:
            print(f"[DEBUG] Keeping temporary file for debugging: {temp_path}")

@app.post("/save-audio")
async def save_audio(file: UploadFile = File(...), keep_debug_files: bool = False):
    """New endpoint that saves the audio file and then processes it with more control"""
    try:
        # Get information about the file
        filename = file.filename
        content_type = file.content_type
        print(f"[DEBUG] Received file: {filename}, Content-Type: {content_type}")
        
        # Generate a unique filename with timestamp
        timestamp = int(time.time())
        audio_path = AUDIO_DIR / f"recording_{timestamp}.mp3"
        
        # Save the file directly
        with open(audio_path, "wb") as f:
            content = await file.read()
            f.write(content)
            
        file_size = audio_path.stat().st_size
        print(f"[DEBUG] Saved audio file to {audio_path}, size: {file_size} bytes")
        
        # Verify the file exists and has content
        if not audio_path.exists() or file_size < 100:
            return {
                "success": False,
                "response": "The audio file is too small or could not be saved.",
                "error": "Invalid audio data"
            }
            
        # Try transcribing using our service
        transcript = None
        try:
            # Pass the keep_files parameter to control whether to delete files after processing
            transcript = transcribe_audio(str(audio_path), keep_files=keep_debug_files)
            print(f"[DEBUG] Successfully transcribed: '{transcript}'")
            
            try:
                # MODIFIED: Process transcript using the CLI-style approach instead of directly calling trip_planner.process
                # Initial state (same as CLI version)
                state = {"query": transcript}
                
                # Step 1: Chat Input Node
                print("[DEBUG] Processing with chat_input_node")
                state = await chat_input_node(state)
                
                # Step 2: Intent Parser Node
                print("[DEBUG] Processing with intent_parser_node")
                state = await intent_parser_node(state)
                
                # Check for errors in intent parsing
                if "error" in state and state["error"]:
                    print(f"[ERROR] Intent parser error: {state['error']}")
                    return {
                        "success": False,
                        "transcript": transcript,
                        "response": f"Failed to understand your travel query: {state['error']}",
                        "error": state["error"]
                    }
                
                # Check if metadata was extracted
                if "metadata" not in state or not state["metadata"]:
                    print("[ERROR] No metadata extracted from query")
                    return {
                        "success": False,
                        "transcript": transcript,
                        "response": "Could not extract travel details from your query",
                        "error": "No metadata was extracted"
                    }
                
                # Step 3: Trip Validator Node
                print("[DEBUG] Processing with trip_validator_node")
                state = await trip_validator_node(state)
                
                # Check if trip is valid
                if not state.get('is_valid', False):
                    return {
                        "success": False,
                        "transcript": transcript,
                        "response": "Your travel query couldn't be processed.",
                        "validation_errors": state.get("validation_errors", ["Unknown validation error"]),
                        "error": "Invalid trip parameters"
                    }
                
                # Step 4: Planner Node
                print("[DEBUG] Processing with planner_node")
                state = await planner_node(state)
                
                # Step 5: Agent Nodes
                nodes_to_call = state.get('nodes_to_call', [])
                print(f"[DEBUG] Nodes to call: {nodes_to_call}")
                
                if 'flights' in nodes_to_call:
                    print("[DEBUG] Processing with flights_node")
                    state = await flights_node(state)
                
                if 'route' in nodes_to_call:
                    print("[DEBUG] Processing with route_node")
                    state = await route_node(state)
                
                if 'places' in nodes_to_call:
                    print("[DEBUG] Processing with places_node")
                    state = await places_node(state)
                
                if 'restaurants' in nodes_to_call:
                    print("[DEBUG] Processing with restaurants_node")
                    state = await restaurants_node(state)
                
                if 'hotel' in nodes_to_call:
                    print("[DEBUG] Processing with hotel_node")
                    state = await hotel_node(state)
                
                if 'budget' in nodes_to_call:
                    print("[DEBUG] Processing with budget_node")
                    state = await budget_node(state)
                
                # Step 6: Reviews Node
                print("[DEBUG] Processing with reviews_node")
                state = await reviews_node(state)
                
                # Step 7: Summary Node
                print("[DEBUG] Processing with summary_node")
                state = await summary_node(state)
                
                # Use the result from the state
                result = state
                print(f"[DEBUG] Final state keys: {result.keys()}")
                
                # Check if there was an error in processing
                if "error" in result and result["error"]:
                    print(f"[ERROR] Trip planner error: {result['error']}")
                    return {
                        "success": False,
                        "transcript": transcript,
                        "response": result.get("response", "I had trouble planning your trip based on that request."),
                        "error": result["error"]
                    }
                
                # Extract a simple text response from the complex result
                response_text = ""
                structured_response = {}
                
                if isinstance(result, dict):
                    # If we have an itinerary and daily_itinerary, return the structured data
                    if "daily_itinerary" in result:
                        print("[DEBUG] Returning structured daily itinerary")
                        return {
                            "success": True,
                            "transcript": transcript,
                            "response": {
                                "trip_summary": result.get("trip_summary", {}),
                                "daily_itinerary": result.get("daily_itinerary", {}),
                                "review_highlights": result.get("review_highlights", {})
                            }
                        }
                    # If we have just a trip_summary
                    elif "trip_summary" in result:
                        print("[DEBUG] Returning trip_summary")
                        summary = result["trip_summary"]
                        response_text = f"Trip to {summary.get('destination', 'your destination')} planned for {summary.get('start_date', 'your dates')}"
                        structured_response = {
                            "trip_summary": summary
                        }
                    # If we have a string itinerary
                    elif "itinerary" in result and result["itinerary"]:
                        print("[DEBUG] Returning itinerary as string or object")
                        if isinstance(result["itinerary"], str):
                            response_text = result["itinerary"]
                        else:
                            # If itinerary is a dict with daily_itinerary
                            if isinstance(result["itinerary"], dict) and "daily_itinerary" in result["itinerary"]:
                                return {
                                    "success": True,
                                    "transcript": transcript,
                                    "response": result["itinerary"]
                                }
                            response_text = f"Generated itinerary for your trip to {result.get('metadata', {}).get('destination', 'your destination')}"
                            structured_response = result["itinerary"]
                    else:
                        response_text = "Your trip has been planned successfully."
                else:
                    response_text = "Thank you for your query. Your trip is being processed."
                
                # Return either structured or simple response
                if structured_response:
                    return {
                        "success": True,
                        "transcript": transcript,
                        "response": structured_response
                    }
                else:
                    return {
                        "success": True,
                        "transcript": transcript,
                        "response": response_text
                    }
            except Exception as planning_error:
                print(f"[ERROR] Trip planning failed: {str(planning_error)}")
                import traceback
                traceback.print_exc()
                return {
                    "success": False,
                    "transcript": transcript,
                    "response": "I understood what you said, but had trouble planning your trip. Could you try again with more details?",
                    "error": str(planning_error)
                }
                
        except Exception as transcription_error:
            print(f"[ERROR] Transcription failed: {str(transcription_error)}")
            # Don't delete files on error for debugging purposes
            return {
                "success": False,
                "response": "I'm having trouble understanding the audio. Could you please speak more clearly or try typing your message instead?",
                "error": str(transcription_error),
                "file_path": str(audio_path)
            }
            
    except Exception as e:
        print(f"[ERROR] Audio processing error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "response": "There was an error processing your audio. Please try again.",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    print("Starting AI Travel Planner API on port 8000...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
