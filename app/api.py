from fastapi import FastAPI, HTTPException, File, UploadFile, WebSocket, WebSocketDisconnect, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Set, Union
import asyncio
import uuid
import os
import json
import time
import logging
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging with a consistent format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("travel_api")

# Suppress other loggers to avoid duplication
logging.getLogger("uvicorn.access").propagate = False
logging.getLogger("uvicorn.error").propagate = False

# Import processing nodes
from app.nodes.chat_input_node import chat_input_node
from app.nodes.intent_parser_node import intent_parser_node
from app.nodes.trip_validator_node import trip_validator_node, process_user_response
from app.nodes.planner_node import planner_node
from app.nodes.agent_nodes import (
    flights_node, places_node, restaurants_node, hotel_node,
    budget_node, reviews_node, route_node
)
from app.nodes.summary_node import summary_node
from app.schemas.trip_schema import TripData

# Import services
from endpoints.services.speech_to_text import transcribe_audio

# Create the FastAPI app
app = FastAPI(
    title="Travel Planning API",
    description="Advanced AI-powered travel planning service",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create dedicated directories
AUDIO_DIR = Path("audio_files")
AUDIO_DIR.mkdir(exist_ok=True)

# In-memory storage
conversation_states: Dict[str, Dict[str, Any]] = {}
active_connections: Dict[str, Set[WebSocket]] = {}
active_jobs: Dict[str, Dict[str, Any]] = {}

#-------------------------------------------------------
# Models
#-------------------------------------------------------

class TravelQuery(BaseModel):
    """Model for natural language travel queries"""
    query: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    interactive: bool = True
    step_by_step: bool = False
    metadata: Optional[Dict[str, Any]] = None

class FlightSelection(BaseModel):
    """Model for flight selection"""
    conversation_id: str
    selection_index: int
    user_id: Optional[str] = None
    step_by_step: bool = False

class FeedbackRequest(BaseModel):
    """Model for providing feedback on an itinerary"""
    conversation_id: str
    category: int = Field(..., ge=1, le=6)  # 1-6 for different categories
    feedback: str
    user_id: Optional[str] = None

class TravelResponse(BaseModel):
    """Unified response model for all travel planning endpoints"""
    request_id: str
    conversation_id: str
    status: str = "success"  # success, error, pending
    message: str
    
    # Content types
    itinerary: Optional[Dict[str, Any]] = None
    trip_summary: Optional[Dict[str, Any]] = None
    daily_plan: Optional[Dict[str, Any]] = None
    flight_options: Optional[List[Dict[str, Any]]] = None
    selected_flight: Optional[Dict[str, Any]] = None
    
    # Interactive elements
    next_interaction: Optional[str] = None  # validation, flight_selection, complete
    next_question: Optional[str] = None
    suggestions: Optional[List[str]] = None
    validation_errors: Optional[List[str]] = None
    
    # State management
    is_valid: Optional[bool] = None
    in_progress: bool = False
    job_id: Optional[str] = None
    error: Optional[str] = None

class AudioProcessRequest(BaseModel):
    """Options for audio processing"""
    keep_debug_files: bool = False
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    step_by_step: bool = False

class JobStatusResponse(BaseModel):
    """Response model for job status checks"""
    job_id: str
    status: str  # pending, complete, failed
    progress: float = 0.0  # 0-1 completion percentage
    message: str
    result_id: Optional[str] = None  # ID to fetch results when complete
    error: Optional[str] = None

#-------------------------------------------------------
# Helper Functions
#-------------------------------------------------------

def generate_id() -> str:
    """Generate a unique ID for requests and jobs"""
    return str(uuid.uuid4())

async def process_nodes(state, nodes_to_call, skip_flight_selection=False):
    """Process the required nodes in sequence"""
    try:
        # Process flight node separately if needed
        if 'flights' in nodes_to_call and not skip_flight_selection:
            logger.info("Processing flights_node")
            state = await flights_node(state)
            
            # Mark state as awaiting flight selection
            if state.get("flights"):
                state["awaiting_flight_selection"] = True
                return state
        
        # Process other nodes
        remaining_nodes = [n for n in nodes_to_call if n != "flights" or skip_flight_selection]
        
        for node in remaining_nodes:
            logger.info(f"Processing node: {node}")
            if node == "route":
                state = await route_node(state)
            elif node == "places":
                state = await places_node(state)
            elif node == "restaurants":
                state = await restaurants_node(state)
            elif node == "hotel":
                state = await hotel_node(state)
            elif node == "budget":
                state = await budget_node(state)
            elif node == "flights" and skip_flight_selection:
                # Only if we're skipping selection and need to process flights
                state = await flights_node(state)
        
        # Process review and summary nodes
        logger.info("Processing reviews_node")
        state = await reviews_node(state)
        
        logger.info("Processing summary_node")
        state = await summary_node(state)
        
        # Mark planning as complete
        state["planning_complete"] = True
        state["nodes_to_call"] = []
        
        return state
    
    except Exception as e:
        logger.error(f"Error in process_nodes: {str(e)}")
        import traceback
        traceback.print_exc()
        state["error"] = str(e)
        return state

async def create_travel_response(state, conversation_id, request_id=None, message=None) -> TravelResponse:
    """Create a standardized response from state"""
    
    if request_id is None:
        request_id = generate_id()
        
    if message is None:
        if state.get("error"):
            message = f"Error: {state['error']}"
        elif state.get("awaiting_flight_selection"):
            message = "Please select your preferred flight"
        elif state.get("itinerary"):
            message = "Your travel itinerary is ready"
        elif state.get("is_valid") is False:
            message = "We need more information for your trip"
        else:
            message = "Processing your travel request"
    
    response = TravelResponse(
        request_id=request_id,
        conversation_id=conversation_id,
        message=message,
        status="success" if not state.get("error") else "error",
        is_valid=state.get("is_valid"),
        error=state.get("error")
    )
    
    # Set validation errors and questions if validation failed
    if state.get("is_valid") is False:
        response.validation_errors = state.get("validation_errors")
        response.next_interaction = "validation"
        response.suggestions = state.get("suggestions", [
            "Try specifying dates in MM/DD/YYYY format",
            "Make sure to include your destination",
            "Specify the number of travelers"
        ])
        
        if state.get("interactive_mode") and state.get("next_question"):
            response.next_question = state.get("next_question")
    
    # Flight selection
    if state.get("awaiting_flight_selection"):
        response.flight_options = state.get("flights")
        response.next_interaction = "flight_selection"
    
    # Selected flight
    if state.get("selected_flights") and len(state.get("selected_flights", [])) > 0:
        response.selected_flight = state.get("selected_flights")[0]
    
    # Itinerary data
    if state.get("itinerary"):
        if isinstance(state["itinerary"], dict):
            response.itinerary = state["itinerary"]
        else:
            response.itinerary = {"full_text": state["itinerary"]}
            
    if state.get("trip_summary"):
        response.trip_summary = state["trip_summary"]
        
    if state.get("daily_itinerary"):
        response.daily_plan = state["daily_itinerary"]
    
    # Set final status if planning is complete
    if state.get("planning_complete"):
        response.next_interaction = "complete"
    
    # In-progress status
    response.in_progress = bool(state.get("awaiting_flight_selection") or 
                               (state.get("interactive_mode") and state.get("next_question")))
    
    return response

async def broadcast_update(conversation_id: str, update_type: str, data: Dict[str, Any]):
    """Send an update to all WebSocket connections for a conversation"""
    if conversation_id in active_connections:
        if "conversation_id" not in data:
            data["conversation_id"] = conversation_id
            
        message = {"type": update_type, "data": data}
        connections = list(active_connections[conversation_id])
        
        # Send to all connections
        results = await asyncio.gather(
            *[conn.send_json(message) for conn in connections],
            return_exceptions=True
        )
        
        # Handle dead connections
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                try:
                    await connections[i].close()
                except:
                    pass
                active_connections[conversation_id].discard(connections[i])
        
        # Clean up empty sets
        if not active_connections[conversation_id]:
            del active_connections[conversation_id]

async def background_process_task(
    job_id: str,
    query: str,
    conversation_id: str,
    state: Dict[str, Any] = None,
    interactive: bool = True,
    step_by_step: bool = False
):
    """Background task for processing travel queries"""
    if state is None:
        state = {"query": query}
    
    try:
        # Update job status
        active_jobs[job_id] = {
            "status": "processing",
            "progress": 0.1,
            "message": "Processing your travel query",
            "conversation_id": conversation_id
        }
        
        # Process through the pipeline nodes
        # Step 1: Chat Input Node
        state = await chat_input_node(state)
        active_jobs[job_id]["progress"] = 0.2
        
        # Step 2: Intent Parser Node
        state = await intent_parser_node(state)
        active_jobs[job_id]["progress"] = 0.3
        
        # Check intent parsing errors
        if state.get("error"):
            active_jobs[job_id]["status"] = "failed"
            active_jobs[job_id]["error"] = state["error"]
            conversation_states[conversation_id] = state
            return
        
        # Check if metadata was extracted
        if not state.get("metadata"):
            state["error"] = "Could not extract travel details from your query"
            state["is_valid"] = False
            active_jobs[job_id]["status"] = "failed"
            active_jobs[job_id]["error"] = state["error"]
            conversation_states[conversation_id] = state
            return
        
        # Step 3: Trip Validator Node
        state = await trip_validator_node(state)
        active_jobs[job_id]["progress"] = 0.4
        
        if not state.get("is_valid", False):
            # Save for interactive follow-up if needed
            conversation_states[conversation_id] = state
            active_jobs[job_id]["status"] = "complete"
            active_jobs[job_id]["result_id"] = conversation_id
            return
        
        # Step 4: Planner Node
        state = await planner_node(state)
        active_jobs[job_id]["progress"] = 0.5
        
        # Step 5: Agent Nodes
        state["step_by_step"] = step_by_step
        nodes_to_call = state.get('nodes_to_call', [])
        
        # Process nodes with or without flight selection based on step_by_step flag
        if step_by_step:
            # Process up to flight selection if flights are in nodes_to_call
            state = await process_nodes(state, nodes_to_call, skip_flight_selection=False)
            active_jobs[job_id]["progress"] = 0.8
        else:
            # Skip flight selection in non-interactive mode, autogenerate itinerary
            state = await process_nodes(state, nodes_to_call, skip_flight_selection=True)
            active_jobs[job_id]["progress"] = 0.9
            
        # Save the state
        conversation_states[conversation_id] = state
        
        # Mark job as complete
        active_jobs[job_id]["status"] = "complete"
        active_jobs[job_id]["progress"] = 1.0
        active_jobs[job_id]["message"] = "Processing complete"
        active_jobs[job_id]["result_id"] = conversation_id
        
        # Send WebSocket update if sockets exist
        update_data = {
            "job_id": job_id,
            "status": "complete", 
            "has_itinerary": state.get("itinerary") is not None,
            "awaiting_flight_selection": state.get("awaiting_flight_selection", False),
            "needs_validation": not state.get("is_valid", False) and state.get("interactive_mode", False)
        }
        await broadcast_update(conversation_id, "job_update", update_data)
        
    except Exception as e:
        logger.error(f"Error in background_process_task: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Update job status on error
        active_jobs[job_id]["status"] = "failed"
        active_jobs[job_id]["error"] = str(e)
        active_jobs[job_id]["progress"] = 1.0
        
        # Save error state
        if conversation_id not in conversation_states:
            conversation_states[conversation_id] = {}
        conversation_states[conversation_id]["error"] = str(e)
        
        # Send error update via WebSocket
        await broadcast_update(
            conversation_id, 
            "processing_error", 
            {"error": str(e), "job_id": job_id}
        )

#-------------------------------------------------------
# API Endpoints
#-------------------------------------------------------

@app.post("/travel/query", response_model=TravelResponse)
async def create_travel_plan(
    request: TravelQuery,
    background_tasks: BackgroundTasks
):
    """
    Process a natural language travel query.
    
    This endpoint accepts free-form travel queries and processes them
    to create a personalized travel itinerary. It uses AI to extract
    travel details, validate the trip parameters, and generate recommendations.
    
    If the query requires additional information, it will enter an interactive
    mode to ask follow-up questions. If flight booking is part of the plan,
    you'll need to select a flight option in a separate step.
    
    Examples:
    ```
    {
        "query": "Plan a trip to Paris for 2 people from Dec 15-20, 2023",
        "interactive": true,
        "step_by_step": true
    }
    ```
    """
    try:
        # Generate IDs
        request_id = generate_id()
        job_id = generate_id()
        
        # If no conversation_id provided, create one
        conversation_id = request.conversation_id or generate_id()
        
        # Initialize state with query
        state = {"query": request.query}
        
        # Add to conversation states (will be updated by background task)
        conversation_states[conversation_id] = state
        
        # Start background processing
        background_tasks.add_task(
            background_process_task,
            job_id=job_id,
            query=request.query,
            conversation_id=conversation_id,
            state=state,
            interactive=request.interactive,
            step_by_step=request.step_by_step
        )
        
        # Return initial response with job_id
        response = TravelResponse(
            request_id=request_id,
            conversation_id=conversation_id,
            status="pending",
            message="Your travel request is being processed",
            in_progress=True,
            job_id=job_id
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in create_travel_plan: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return TravelResponse(
            request_id=generate_id(),
            conversation_id=request.conversation_id or generate_id(),
            status="error",
            message="Failed to process travel query",
            error=str(e)
        )

@app.get("/travel/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Check the status of a travel planning job.
    
    After submitting a query to `/travel/query`, you can use this endpoint
    to poll the status of the processing job until it's complete.
    Once the job is marked as complete, you can fetch the results using
    the `/travel/results/{conversation_id}` endpoint with the `result_id`.
    """
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = active_jobs[job_id]
    
    return JobStatusResponse(
        job_id=job_id,
        status=job.get("status", "pending"),
        progress=job.get("progress", 0.0),
        message=job.get("message", "Job is being processed"),
        result_id=job.get("result_id"),
        error=job.get("error")
    )

@app.get("/travel/results/{conversation_id}", response_model=TravelResponse)
async def get_travel_results(conversation_id: str):
    """
    Get the results of a travel planning query.
    
    After a job is complete, use this endpoint to retrieve the full
    travel plan, including itinerary, flight options, and any interactive
    steps needed to complete the planning process.
    """
    if conversation_id not in conversation_states:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    state = conversation_states[conversation_id]
    
    return await create_travel_response(
        state=state,
        conversation_id=conversation_id,
        request_id=generate_id()
    )

@app.post("/travel/select-flight", response_model=TravelResponse)
async def select_flight(
    request: FlightSelection,
    background_tasks: BackgroundTasks
):
    """
    Select a flight from the available options.
    
    After receiving flight options from a travel query, use this endpoint
    to select your preferred flight. This will update your itinerary with
    the selected flight details and continue processing the remaining parts
    of your travel plan.
    
    In step-by-step mode, this will only confirm your selection without
    completing the full itinerary. You'll need to make a subsequent request
    to complete the planning process.
    """
    try:
        conversation_id = request.conversation_id
        
        # Check if conversation exists
        if conversation_id not in conversation_states:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        state = conversation_states[conversation_id]
        
        # Check if we're awaiting flight selection
        if not state.get("awaiting_flight_selection"):
            raise HTTPException(status_code=400, detail="Not awaiting flight selection")
        
        # Check if we have flights
        if not state.get("flights") or len(state["flights"]) == 0:
            raise HTTPException(status_code=400, detail="No flight options available")
        
        # Validate selection index
        if request.selection_index < 0 or request.selection_index >= len(state["flights"]):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid selection index. Must be between 0 and {len(state['flights'])-1}"
            )
        
        # Get selected flight
        selected_flight = state["flights"][request.selection_index]
        
        # Update state
        state["selected_flights"] = [selected_flight]
        state["awaiting_flight_selection"] = False
        
        # Save updated state
        conversation_states[conversation_id] = state
        
        # If step-by-step mode, just return confirmation
        if request.step_by_step:
            return TravelResponse(
                request_id=generate_id(),
                conversation_id=conversation_id,
                status="success",
                message="Flight selected. Ready to continue planning.",
                selected_flight=selected_flight,
                in_progress=True,
                next_interaction="continue"
            )
        
        # Otherwise continue processing in background
        job_id = generate_id()
        
        # Start background processing for remaining nodes
        background_tasks.add_task(
            background_process_task,
            job_id=job_id,
            query=state.get("query", ""),
            conversation_id=conversation_id,
            state=state,
            interactive=True,
            step_by_step=False
        )
        
        # Return immediate response with job_id
        return TravelResponse(
            request_id=generate_id(),
            conversation_id=conversation_id,
            status="pending",
            message="Flight selected. Completing your travel plan...",
            selected_flight=selected_flight,
            in_progress=True,
            job_id=job_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in select_flight: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return TravelResponse(
            request_id=generate_id(),
            conversation_id=request.conversation_id,
            status="error",
            message="Failed to process flight selection",
            error=str(e)
        )

@app.post("/travel/continue", response_model=TravelResponse)
async def continue_planning(request: FlightSelection, background_tasks: BackgroundTasks):
    """
    Continue planning after flight selection in step-by-step mode.
    
    After selecting a flight in step-by-step mode, use this endpoint
    to continue the planning process and generate the complete itinerary.
    """
    try:
        conversation_id = request.conversation_id
        
        # Check if conversation exists
        if conversation_id not in conversation_states:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        state = conversation_states[conversation_id]
        
        # Check if we have selected flights
        if not state.get("selected_flights"):
            raise HTTPException(status_code=400, detail="No flight has been selected")
        
        # Start background processing for remaining nodes
        job_id = generate_id()
        
        # In this case, we have already saved the selected flight in the state,
        # so we continue processing with the existing state
        background_tasks.add_task(
            background_process_task,
            job_id=job_id,
            query=state.get("query", ""),
            conversation_id=conversation_id,
            state=state,
            interactive=True,
            step_by_step=False  # No longer step-by-step since we're continuing
        )
        
        # Return immediate response with job_id
        return TravelResponse(
            request_id=generate_id(),
            conversation_id=conversation_id,
            status="pending",
            message="Continuing with your travel plan...",
            selected_flight=state.get("selected_flights", [{}])[0],
            in_progress=True,
            job_id=job_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in continue_planning: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return TravelResponse(
            request_id=generate_id(),
            conversation_id=request.conversation_id,
            status="error",
            message="Failed to continue planning",
            error=str(e)
        )

@app.post("/travel/feedback", response_model=TravelResponse)
async def provide_feedback(request: FeedbackRequest, background_tasks: BackgroundTasks):
    """
    Provide feedback to modify an existing itinerary.
    
    After receiving a complete itinerary, use this endpoint to request
    modifications based on your preferences. The feedback will be processed
    to update your travel plan accordingly.
    """
    try:
        conversation_id = request.conversation_id
        
        # Check if conversation exists
        if conversation_id not in conversation_states:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        state = conversation_states[conversation_id]
        
        # Check if we have an itinerary
        if not state.get("itinerary"):
            raise HTTPException(status_code=400, detail="No itinerary available to modify")
        
        # Format feedback
        feedback = {
            "category": request.category,
            "feedback": request.feedback
        }
        
        # Process feedback (assuming we have a function to process feedback)
        # This would typically update the state with feedback and mark nodes for reprocessing
        from app.pipeline import process_feedback
        state = await process_feedback(state, feedback)
        
        # Start background processing to update the itinerary
        job_id = generate_id()
        
        background_tasks.add_task(
            background_process_task,
            job_id=job_id,
            query=state.get("query", ""),
            conversation_id=conversation_id,
            state=state,
            interactive=True,
            step_by_step=False
        )
        
        # Return immediate response with job_id
        return TravelResponse(
            request_id=generate_id(),
            conversation_id=conversation_id,
            status="pending",
            message="Processing your feedback...",
            in_progress=True,
            job_id=job_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in provide_feedback: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return TravelResponse(
            request_id=generate_id(),
            conversation_id=request.conversation_id,
            status="error",
            message="Failed to process feedback",
            error=str(e)
        )

@app.post("/travel/voice", response_model=TravelResponse)
async def process_voice_input(
    file: UploadFile = File(...),
    options: AudioProcessRequest = Depends(),
    background_tasks: BackgroundTasks = None,
):
    """
    Process a voice recording for travel planning.
    
    Upload an audio file containing your travel query, which will be
    transcribed and processed through the travel planning pipeline.
    
    This is equivalent to using the `/travel/query` endpoint with a
    text query, but accepts audio input instead.
    """
    temp_path = None
    audio_path = None
    
    try:
        # Generate IDs
        request_id = generate_id()
        job_id = generate_id()
        conversation_id = options.conversation_id or generate_id()
        
        # Save the audio file
        filename = file.filename
        original_ext = os.path.splitext(filename)[1] or ".mp3"
        
        # Use temporary file for initial save
        with tempfile.NamedTemporaryFile(delete=False, suffix=original_ext) as temp:
            shutil.copyfileobj(file.file, temp)
            temp_path = temp.name
        
        # If keep_debug_files is True, also save to persistent location
        if options.keep_debug_files:
            timestamp = int(time.time())
            audio_path = AUDIO_DIR / f"recording_{timestamp}{original_ext}"
            shutil.copy2(temp_path, audio_path)
        
        # Transcribe the audio
        transcript = transcribe_audio(temp_path, keep_files=options.keep_debug_files)
        
        if not transcript:
            return TravelResponse(
                request_id=request_id,
                conversation_id=conversation_id,
                status="error",
                message="Could not transcribe audio",
                error="Failed to extract speech from audio file"
            )
        
        # Initialize state with transcript as query
        state = {"query": transcript}
        
        # Add to conversation states (will be updated by background task)
        conversation_states[conversation_id] = state
        
        # Start background processing
        background_tasks.add_task(
            background_process_task,
            job_id=job_id,
            query=transcript,
            conversation_id=conversation_id,
            state=state,
            interactive=True,
            step_by_step=options.step_by_step
        )
        
        # Return initial response with job_id and transcript
        return TravelResponse(
            request_id=request_id,
            conversation_id=conversation_id,
            status="pending",
            message=f"Processing your audio query: '{transcript}'",
            in_progress=True,
            job_id=job_id
        )
        
    except Exception as e:
        logger.error(f"Error in process_voice_input: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return TravelResponse(
            request_id=generate_id(),
            conversation_id=options.conversation_id or generate_id(),
            status="error",
            message="Failed to process voice input",
            error=str(e)
        )
    finally:
        # Clean up the temporary file
        if temp_path and os.path.exists(temp_path) and not options.keep_debug_files:
            try:
                os.remove(temp_path)
            except:
                pass

@app.get("/travel/conversations")
async def list_conversations():
    """List all active conversation IDs."""
    return {
        "conversations": list(conversation_states.keys()),
        "count": len(conversation_states)
    }

@app.get("/travel/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get details of a specific conversation."""
    if conversation_id not in conversation_states:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    state = conversation_states[conversation_id]
    
    # Return a summary of the conversation state
    return {
        "conversation_id": conversation_id,
        "has_query": "query" in state,
        "is_valid": state.get("is_valid", False),
        "has_itinerary": "itinerary" in state,
        "awaiting_flight_selection": state.get("awaiting_flight_selection", False),
        "planning_complete": state.get("planning_complete", False),
        "has_error": "error" in state,
        "metadata": state.get("metadata"),
        "updated_at": datetime.now().isoformat()
    }

@app.delete("/travel/conversation/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation state."""
    if conversation_id not in conversation_states:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    del conversation_states[conversation_id]
    
    # Also remove from WebSocket connections if present
    if conversation_id in active_connections:
        # Close all connections
        for connection in active_connections[conversation_id]:
            try:
                await connection.close()
            except:
                pass
        del active_connections[conversation_id]
    
    return {"message": f"Conversation {conversation_id} deleted"}

@app.websocket("/ws/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    """
    WebSocket endpoint for real-time trip planning updates.
    
    Connect to this WebSocket to receive real-time updates about your
    travel planning process, including status changes, processing steps,
    and completion notifications.
    """
    await websocket.accept()
    
    # Register connection
    if conversation_id not in active_connections:
        active_connections[conversation_id] = set()
    active_connections[conversation_id].add(websocket)
    
    try:
        # Send initial state if conversation exists
        if conversation_id in conversation_states:
            state = conversation_states[conversation_id]
            initial_update = {
                "type": "state_update",
                "data": {
                    "conversation_id": conversation_id,
                    "has_query": "query" in state,
                    "is_valid": state.get("is_valid", False),
                    "has_itinerary": "itinerary" in state,
                    "awaiting_flight_selection": state.get("awaiting_flight_selection", False),
                    "planning_complete": state.get("planning_complete", False),
                    "has_error": "error" in state
                }
            }
            await websocket.send_json(initial_update)
        
        # Listen for messages (ping/pong, etc.)
        async for message in websocket.iter_json():
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong", "timestamp": time.time()})
            elif message.get("type") == "request_state":
                # Client requested current state
                if conversation_id in conversation_states:
                    state = conversation_states[conversation_id]
                    await websocket.send_json({
                        "type": "state_update",
                        "data": {
                            "conversation_id": conversation_id,
                            "has_query": "query" in state,
                            "is_valid": state.get("is_valid", False),
                            "has_itinerary": "itinerary" in state,
                            "awaiting_flight_selection": state.get("awaiting_flight_selection", False),
                            "planning_complete": state.get("planning_complete", False),
                            "has_error": "error" in state
                        }
                    })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for conversation: {conversation_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket: {str(e)}")
    finally:
        # Remove connection
        if conversation_id in active_connections:
            active_connections[conversation_id].discard(websocket)
            if not active_connections[conversation_id]:
                del active_connections[conversation_id]

@app.get("/")
async def root():
    """API root endpoint with documentation links."""
    return {
        "message": "Travel Planning API",
        "version": "2.0.0",
        "documentation": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "travel": {
                "query": "/travel/query - Create a new travel plan",
                "status": "/travel/status/{job_id} - Check job status",
                "results": "/travel/results/{conversation_id} - Get travel results",
                "select_flight": "/travel/select-flight - Select a flight option",
                "continue": "/travel/continue - Continue planning after flight selection",
                "feedback": "/travel/feedback - Provide feedback on itinerary",
                "voice": "/travel/voice - Process voice input"
            },
            "websocket": "/ws/{conversation_id} - Real-time updates"
        }
    }

# For running directly with uvicorn
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    dev_mode = os.getenv("DEV_MODE", "False").lower() in ("true", "1", "t")
    
    print("\n✨ Starting Travel Planning API ✨")
    
    uvicorn.run(
        "app.api:app",
        host="0.0.0.0",
        port=port,
        reload=dev_mode
    ) 