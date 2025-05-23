from fastapi import FastAPI, HTTPException, File, UploadFile, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from app.graph.trip_planner_graph import TripPlannerGraph
from app.schemas.trip_schema import TripData, TripMetadata
from typing import Optional, List, Dict, Any, Set
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
from dotenv import load_dotenv
import logging
import asyncio
import json

# Import our utility modules
from app.utils.logger import logger
from app.utils.anthropic_client import anthropic_client

# Import our pipeline functions
from app.pipeline import process_travel_query, process_feedback, Spinner

# Load environment variables from .env file (same as CLI version)
load_dotenv()

# Configure logging with a consistent format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # Console handler without duplicates
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("app")

# Prevent duplicate logs from Uvicorn
logging.getLogger("uvicorn.access").propagate = False
logging.getLogger("uvicorn.error").propagate = False

# Import our consolidated validator
from app.nodes.trip_validator_node import trip_validator_node, process_user_response
from app.nodes.chat_input_node import chat_input_node
from app.nodes.intent_parser_node import intent_parser_node
# Add missing node imports
from app.nodes.planner_node import planner_node
from app.nodes.agent_nodes import flights_node, places_node, restaurants_node, hotel_node, budget_node, reviews_node, route_node
from app.nodes.summary_node import summary_node
# Import flight selection node
from app.nodes.flight_selection_node import display_flight_options, get_user_flight_selection

# Import our flight booking router
from app.api.flight_booking import router as flight_booking_router

# Additional configuration for when using Gunicorn with worker processes
# This helps prevent issues with multiple workers processing the same request
# Gunicorn will automatically detect these settings
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
keepalive = 5
timeout = 120

# Create the FastAPI app
app = FastAPI(
    title="AI Travel Planner",
    description="AI-powered travel planning service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

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

# Dictionary to store active WebSocket connections by conversation ID
active_connections: Dict[str, Set[WebSocket]] = {}

class AnalyzeInputRequest(BaseModel):
    """Request model for analyzing user input."""
    input: str
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ChatRequest(BaseModel):
    """Request model for all chat-based interactions."""
    message: Optional[str] = None  # Text input from user
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    interaction_type: Optional[str] = None  # 'chat', 'flight_selection', 'feedback', etc.
    selection_data: Optional[Dict[str, Any]] = None  # For selections like flight choice
    metadata: Optional[Dict[str, Any]] = None  # Additional context/data

class InteractionResponse(BaseModel):
    """Unified response model for all interactions."""
    conversation_id: str
    success: bool
    message: str  # Human readable response
    data: Optional[Dict[str, Any]] = None  # Structured data (itinerary, flights, etc)
    interaction_type: Optional[str] = None  # Type of interaction expected next
    available_actions: Optional[List[Dict[str, Any]]] = None  # Possible next actions
    error: Optional[str] = None

@app.post("/interact", response_model=InteractionResponse)
async def handle_interaction(request: ChatRequest):
    """
    Unified endpoint for all types of interactions.
    Handles: chat messages, flight selection, feedback, and other interactions.
    """
    try:
        # Setup a proper logger
        logger.info(f"Received interaction: {request.dict()}")
        
        # Initialize or get conversation state
        state = conversation_states.get(request.conversation_id, {})
        if not request.conversation_id:
            request.conversation_id = str(uuid.uuid4())
            
        # Send processing update via WebSocket
        await broadcast_update(
            request.conversation_id,
            "processing_started",
            {"message": "Processing your request..."}
        )
            
        # Handle different types of interactions
        if request.interaction_type == "flight_selection":
            result = await handle_flight_interaction(request, state)
        elif request.interaction_type == "feedback":
            result = await handle_feedback_interaction(request, state)
        else:  # Default to chat interaction
            if not request.message:
                return InteractionResponse(
                    conversation_id=request.conversation_id,
                    success=False,
                    message="Message cannot be empty",
                    error="No message provided"
                )
            result = await handle_chat_interaction(request, state)
            
        # Send completion update via WebSocket
        await broadcast_update(
            request.conversation_id,
            "processing_complete",
            {
                "success": result.success,
                "interaction_type": result.interaction_type,
                "has_data": result.data is not None
            }
        )
            
        return result
            
    except Exception as e:
        logger.error(f"Error in handle_interaction: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Send error update via WebSocket
        if request.conversation_id:
            await broadcast_update(
                request.conversation_id,
                "processing_error",
                {"error": str(e)}
            )
            
        return InteractionResponse(
            conversation_id=request.conversation_id,
            success=False,
            message=f"An error occurred: {str(e)}",
            error=str(e)
        )

async def handle_chat_interaction(request: ChatRequest, state: Dict[str, Any]) -> InteractionResponse:
    """Handle general chat interactions."""
    logger.info(f"Processing chat message: '{request.message}'")
    try:
        # Process the chat message
        state["query"] = request.message
        
        # Only process if not already processed
        if not state.get("planning_complete"):
            logger.info(f"Processing chat message: '{request.message}'")
            state = await process_travel_query(request.message)
            conversation_states[request.conversation_id] = state
        else:
            logger.info("Skipping processing - planning already complete")
        
        # If validation failed
        if not state.get("is_valid", False):
            logger.warning("Validation failed for chat message")
            return InteractionResponse(
                conversation_id=request.conversation_id,
                success=True,
                message=state.get("error", "Please provide more details."),
                interaction_type="validation",
                available_actions=[{
                    "type": "suggestion",
                    "items": state.get("suggestions", [
                        "Try specifying dates in MM/DD/YYYY format",
                        "Make sure to include your destination",
                        "Specify the number of travelers"
                    ])
                }]
            )
            
        # If we need flight selection
        if state.get("flights") and not state.get("selected_flights"):
            logger.info("Flight selection needed")
            return InteractionResponse(
                conversation_id=request.conversation_id,
                success=True,
                message="Please select your preferred flight:",
                interaction_type="flight_selection",
                data={"flights": state.get("flights", [])},
                available_actions=[{
                    "type": "selection",
                    "items": [{"id": idx, "data": flight} for idx, flight in enumerate(state.get("flights", []))]
                }]
            )
            
        # If we have a complete itinerary
        if state.get("itinerary"):
            logger.info("Returning complete itinerary")
            return InteractionResponse(
                conversation_id=request.conversation_id,
                success=True,
                message="Here's your travel itinerary. Would you like to modify anything?",
                data={
                    "itinerary": state.get("itinerary"),
                    "trip_summary": state.get("trip_summary", {}),
                    "daily_itinerary": state.get("daily_itinerary", {})
                },
                interaction_type="feedback",
                available_actions=[{
                    "type": "modification",
                    "items": [
                        {"id": "1", "category": "Transportation", "description": "Modify flights/routes"},
                        {"id": "2", "category": "Accommodations", "description": "Change hotel selection"},
                        {"id": "3", "category": "Activities", "description": "Modify places to visit"},
                        {"id": "4", "category": "Dining", "description": "Change restaurant options"},
                        {"id": "5", "category": "Schedule", "description": "Adjust timing of activities"},
                        {"id": "6", "category": "Budget", "description": "Modify costs/budget"}
                    ]
                }]
            )
            
        # Default response for other cases
        return InteractionResponse(
            conversation_id=request.conversation_id,
            success=True,
            message="I'm processing your request. Please provide more details if needed.",
            interaction_type="chat"
        )
        
    except Exception as e:
        logger.error(f"Error in handle_chat_interaction: {str(e)}")
        raise

async def handle_flight_interaction(request: ChatRequest, state: Dict[str, Any]) -> InteractionResponse:
    """Handle flight selection interactions."""
    try:
        if not state.get("flights"):
            return InteractionResponse(
                conversation_id=request.conversation_id,
                success=False,
                message="No flights available for selection.",
                error="No flights in current state"
            )
            
        selection_data = request.selection_data
        if not selection_data or "flight_index" not in selection_data:
            return InteractionResponse(
                conversation_id=request.conversation_id,
                success=False,
                message="Please provide a flight selection.",
                error="Missing flight selection"
            )
            
        flight_index = selection_data["flight_index"]
        selected_flight = state["flights"][flight_index]
        
        # Update state with selection
        state["selected_flights"] = [selected_flight]
        state["awaiting_flight_selection"] = False
        conversation_states[request.conversation_id] = state
        
        # Process remaining nodes
        nodes_to_call = state.get('nodes_to_call', [])
        state = await process_remaining_nodes(state, nodes_to_call, request.conversation_id)
        
        # Return response with updated itinerary
        return InteractionResponse(
            conversation_id=request.conversation_id,
            success=True,
            message="Flight selected! Here's your updated itinerary:",
            data={
                "selected_flight": selected_flight,
                "itinerary": state.get("itinerary"),
                "trip_summary": state.get("trip_summary", {}),
                "daily_itinerary": state.get("daily_itinerary", {})
            },
            interaction_type="feedback",
            available_actions=[{
                "type": "modification",
                "items": [
                    {"id": "1", "category": "Transportation", "description": "Modify flights/routes"},
                    {"id": "2", "category": "Accommodations", "description": "Change hotel selection"},
                    {"id": "3", "category": "Activities", "description": "Modify places to visit"},
                    {"id": "4", "category": "Dining", "description": "Change restaurant options"},
                    {"id": "5", "category": "Schedule", "description": "Adjust timing of activities"},
                    {"id": "6", "category": "Budget", "description": "Modify costs/budget"}
                ]
            }]
        )
        
    except Exception as e:
        print(f"[ERROR] Error in handle_flight_interaction: {str(e)}")
        raise

async def handle_feedback_interaction(request: ChatRequest, state: Dict[str, Any]) -> InteractionResponse:
    """Handle feedback and modification requests."""
    try:
        if not request.selection_data or "category_id" not in request.selection_data:
            return InteractionResponse(
                conversation_id=request.conversation_id,
                success=False,
                message="Please specify what you'd like to modify.",
                error="Missing feedback category"
            )
            
        # Process the feedback
        feedback = {
            "category": int(request.selection_data["category_id"]),
            "feedback": request.selection_data.get("specific_feedback", "")
        }
        
        state = await process_feedback(state, feedback)
        conversation_states[request.conversation_id] = state
        
        return InteractionResponse(
            conversation_id=request.conversation_id,
            success=True,
            message="I've updated your itinerary based on your feedback. Would you like to make any other changes?",
            data={
                "itinerary": state.get("itinerary"),
                "trip_summary": state.get("trip_summary", {}),
                "daily_itinerary": state.get("daily_itinerary", {})
            },
            interaction_type="feedback",
            available_actions=[{
                "type": "modification",
                "items": [
                    {"id": "1", "category": "Transportation", "description": "Modify flights/routes"},
                    {"id": "2", "category": "Accommodations", "description": "Change hotel selection"},
                    {"id": "3", "category": "Activities", "description": "Modify places to visit"},
                    {"id": "4", "category": "Dining", "description": "Change restaurant options"},
                    {"id": "5", "category": "Schedule", "description": "Adjust timing of activities"},
                    {"id": "6", "category": "Budget", "description": "Modify costs/budget"}
                ]
            }]
        )
        
    except Exception as e:
        print(f"[ERROR] Error in handle_feedback_interaction: {str(e)}")
        raise

@app.post("/chat", response_model=InteractionResponse)
async def chat_query(request: ChatRequest):
    """Deprecated: Use /interact endpoint instead."""
    if not request.message:
        return InteractionResponse(
            conversation_id=request.conversation_id or str(uuid.uuid4()),
            success=False,
            message="Message cannot be empty",
            error="No message provided"
        )
    # Don't call handle_interaction again, just forward to /interact endpoint
    return await handle_interaction(request)

@app.post("/feedback", response_model=InteractionResponse)
async def process_feedback_deprecated(request: ChatRequest):
    """Deprecated: Use /interact endpoint instead."""
    request.interaction_type = "feedback"
    return await handle_interaction(request)

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
            "/interact": "For all types of interactions",
            "/generate-itinerary": "For structured trip data",
            "/conversations": "Create new conversations",
            "/search": "Search for travel options"
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

@app.post("/continue-processing", response_model=InteractionResponse)
async def continue_processing(request: ChatRequest):
    """
    Continue processing a conversation after a flight has been selected.
    This is used in step-by-step mode to allow the frontend to fetch the final itinerary.
    """
    try:
        print(f"[DEBUG] Continue processing request: {request.dict()}")
        
        # Ensure we have a valid conversation ID
        if not request.conversation_id:
            print("[ERROR] Missing conversation_id in continue-processing request")
            return InteractionResponse(
                conversation_id=None,
                success=False,
                message="Missing conversation ID",
                error="Missing conversation ID"
            )
            
        if request.conversation_id not in conversation_states:
            print(f"[ERROR] Invalid conversation ID: {request.conversation_id}")
            return InteractionResponse(
                conversation_id=request.conversation_id,
                success=False,
                message="Invalid conversation ID",
                error="Invalid conversation ID"
            )
        
        # Get the conversation state
        state = conversation_states[request.conversation_id]
        print(f"[DEBUG] Conversation state keys: {state.keys()}")
        
        # Check if we just completed a flight selection
        if state.get("selected_flights") and not state.get("planning_complete"):
            # Get the nodes that need processing
            nodes_to_call = state.get('nodes_to_call', [])
            print(f"[DEBUG] Continuing with remaining nodes: {nodes_to_call}")
            
            # Process the remaining nodes
            return await process_remaining_nodes(state, nodes_to_call, request.conversation_id)
        elif state.get("planning_complete"):
            # If planning is already complete, just return the itinerary
            print("[DEBUG] Planning is already complete, returning itinerary")
            return await process_travel_query(state["query"])
        else:
            # No flight selection was done, or we're in an unexpected state
            print(f"[ERROR] Unexpected state in continue-processing. selected_flights: {state.get('selected_flights')}, planning_complete: {state.get('planning_complete')}")
            print(f"[DEBUG] State contains keys: {state.keys()}")
            return InteractionResponse(
                conversation_id=request.conversation_id,
                success=False,
                message="No pending operations to continue",
                error="No pending operations to continue"
            )
        
    except Exception as e:
        print(f"[ERROR] Error in continue_processing: {str(e)}")
        import traceback
        traceback.print_exc()
        return InteractionResponse(
            conversation_id=request.conversation_id,
            success=False,
            message=f"An error occurred while continuing processing: {str(e)}",
            error=str(e)
        )

@app.websocket("/ws/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    """
    WebSocket endpoint for real-time trip planning updates.
    
    Instead of making multiple HTTP requests, clients can subscribe to trip planning
    progress through this WebSocket connection to get real-time updates.
    """
    # Accept the WebSocket connection
    await websocket.accept()
    
    # Register the connection
    if conversation_id not in active_connections:
        active_connections[conversation_id] = set()
    active_connections[conversation_id].add(websocket)
    
    logger.info(f"WebSocket connection established for conversation: {conversation_id}")
    
    try:
        # Send initial state if it exists
        if conversation_id in conversation_states:
            await websocket.send_json({
                "type": "state_update",
                "data": {
                    "state": "current",
                    "planning_complete": conversation_states[conversation_id].get("planning_complete", False),
                    "awaiting_flight_selection": conversation_states[conversation_id].get("awaiting_flight_selection", False),
                    "itinerary": conversation_states[conversation_id].get("itinerary", None) is not None
                }
            })
        
        # Listen for messages from the client
        async for message in websocket.iter_json():
            if message.get("type") == "ping":
                # Respond to ping messages to keep the connection alive
                await websocket.send_json({"type": "pong", "timestamp": time.time()})
            elif message.get("type") == "request_state":
                # Client is requesting current state
                if conversation_id in conversation_states:
                    await websocket.send_json({
                        "type": "state_update",
                        "data": {
                            "state": "current",
                            "planning_complete": conversation_states[conversation_id].get("planning_complete", False),
                            "awaiting_flight_selection": conversation_states[conversation_id].get("awaiting_flight_selection", False),
                            "itinerary": conversation_states[conversation_id].get("itinerary", None) is not None
                        }
                    })
    except WebSocketDisconnect:
        logger.info(f"WebSocket connection closed for conversation: {conversation_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {str(e)}")
    finally:
        # Remove the connection when it's closed
        if conversation_id in active_connections:
            active_connections[conversation_id].discard(websocket)
            if not active_connections[conversation_id]:
                del active_connections[conversation_id]

# Helper function to broadcast updates to all connected WebSocket clients for a conversation
async def broadcast_update(conversation_id: str, update_type: str, data: Dict[str, Any]):
    """Send an update to all WebSocket connections for a specific conversation."""
    if conversation_id in active_connections:
        connections = active_connections[conversation_id]
        dead_connections = set()
        
        for connection in connections:
            try:
                await connection.send_json({
                    "type": update_type,
                    "data": data
                })
            except Exception:
                # Mark connection for removal if it's dead
                dead_connections.add(connection)
        
        # Remove dead connections
        for dead in dead_connections:
            connections.discard(dead)

async def process_travel_query(query: str) -> dict:
    """
    Process a travel query through the validation and planning pipeline.
    
    Args:
        query: User's travel query
        
    Returns:
        dict: Results containing trip details or error message
    """
    try:
        # Initialize state
        state = {
            "query": query,
            "raw_query": query,
            "is_valid": False,
            "metadata": None,
            "next_question": None,
            "error": None
        }
        
        # Create graph instance
        graph = TripPlannerGraph()
        
        # Process query
        result = await graph.process(state)
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return {
            "is_valid": False,
            "error": str(e)
        }

async def main():
    print("=" * 80)
    print("🌍 Welcome to TripIntelAI - Your AI Travel Planner 🌍")
    print("=" * 80)
    print("Please enter your travel query. For example:")
    print("  'I want to plan a trip from Boston to NYC from May 15 to May 18, 2025 for 2 people'")
    print("  'Plan a family vacation to Paris in summer for 5 days with focus on museums'")
    print("-" * 80)
    
    while True:
        # Get user input
        query = input("\nEnter your travel query (or 'exit' to quit): ")
        
        if query.lower() in ['exit', 'quit', 'q']:
            print("\nThank you for using TripIntelAI. Have a great trip! 👋")
            break
        
        if not query.strip():
            print("Please enter a valid query.")
            continue
        
        try:
            # Process the query
            result = await process_travel_query(query)
            
            # Handle results
            if result.get("is_valid", False):
                if "itinerary" in result:
                    print("\n✨ Your personalized travel itinerary: ✨\n")
                    print("-" * 80)
                    print(result["itinerary"])
                    print("-" * 80)
                else:
                    print("\n✅ Trip details validated successfully!")
                    print("Please provide more information to complete your itinerary.")
            else:
                print("\n❌ Your travel query couldn't be processed:")
                if result.get("error"):
                    print(f"  - {result['error']}")
                print("\nPlease try again with more specific information.")
            
        except Exception as e:
            print(f"\n❌ An error occurred: {str(e)}")
            print("Please try again with a different query.")
        
        # Ask if user wants to plan another trip
        another = input("\nWould you like to plan another trip? (y/n): ")
        if another.lower() not in ['y', 'yes']:
            print("\nThank you for using TripIntelAI. Have a great trip! 👋")
            break

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())
