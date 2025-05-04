import asyncio
import os
import time
import threading
from dotenv import load_dotenv
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the individual components
from app.nodes.chat_input_node import chat_input_node
from app.nodes.intent_parser_node import intent_parser_node
from app.nodes.trip_validator_node import trip_validator_node
from app.nodes.planner_node import planner_node
from app.nodes.agent_nodes import flights_node, route_node, places_node, restaurants_node, hotel_node, budget_node, reviews_node
from app.nodes.flight_selection_node import display_flight_options, get_user_flight_selection
from app.nodes.summary_node import summary_node
from app.nodes.feedback_parser_node import feedback_parser_node
from app.nodes.replanning_node import replanning_node

# Load environment variables
load_dotenv()

class Spinner:
    """Simple spinner animation for loading status"""
    def __init__(self, message="Processing"):
        self.message = message
        self.spinning = False
        self.spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.spinner_thread = None

    def spin(self):
        i = 0
        while self.spinning:
            i = (i + 1) % len(self.spinner_chars)
            print(f"\r{self.spinner_chars[i]} {self.message}...", end="", flush=True)
            time.sleep(0.1)

    def start(self):
        self.spinning = True
        self.spinner_thread = threading.Thread(target=self.spin)
        self.spinner_thread.daemon = True
        self.spinner_thread.start()

    def stop(self):
        self.spinning = False
        if self.spinner_thread:
            self.spinner_thread.join()
        print("\r", end="", flush=True)

async def process_nodes(state, nodes_to_process, spinner=None):
    """
    Process a list of nodes with appropriate spinner messages.
    
    Args:
        state: Current graph state
        nodes_to_process: List of node names to process
        spinner: Optional Spinner instance for loading states
        
    Returns:
        Updated state after processing all nodes
    """
    for node in nodes_to_process:
        if node == "flights":
            if spinner:
                spinner.message = "Searching for flights"
            state = await flights_node(state)
            
            # Flight selection if needed
            if state.get("flights", []):
                if spinner:
                    spinner.stop()
                await display_flight_options(state["flights"])
                selection_idx = await get_user_flight_selection(state["flights"])
                state["selected_flights"] = [state["flights"][selection_idx]]
                if spinner:
                    spinner.start()
                
        elif node == "route":
            if spinner:
                spinner.message = "Calculating routes and distances"
            state = await route_node(state)
            
        elif node == "places":
            if spinner:
                spinner.message = "Finding interesting places to visit"
            state = await places_node(state)
            
        elif node == "restaurants":
            if spinner:
                spinner.message = "Discovering local restaurants"
            state = await restaurants_node(state)
            
        elif node == "hotel":
            if spinner:
                spinner.message = "Locating suitable accommodations"
            state = await hotel_node(state)
            
        elif node == "budget":
            if spinner:
                spinner.message = "Calculating trip budget"
            state = await budget_node(state)
    
    return state

async def process_travel_query(query, spinner=None, interactive=False):
    """
    Process a travel query with feedback loop capability.
    
    Args:
        query: User's travel query
        spinner: Optional Spinner instance for loading states
        interactive: Whether to run in interactive mode
        
    Returns:
        Final state after processing and any feedback iterations
    """
    # Initial state
    state = {"query": query}
    
    try:
        # Step 1: Chat Input Node
        if spinner:
            spinner.message = "Parsing your travel query"
        logger.info("Step 1: Processing with chat_input_node")
        state = await chat_input_node(state)
        
        # Step 2: Intent Parser Node
        if spinner:
            spinner.message = "Extracting travel details"
        logger.info("Step 2: Processing with intent_parser_node")
        state = await intent_parser_node(state)
        
        # Check for errors in intent parsing
        if "error" in state and state["error"]:
            logger.error(f"Intent parser error: {state['error']}")
            return {
                "is_valid": False,
                "validation_errors": [f"Failed to understand your travel query: {state['error']}"],
                "error": state["error"]
            }
        
        # Check if metadata was extracted
        if "metadata" not in state or not state["metadata"]:
            logger.error("No metadata extracted from query")
            return {
                "is_valid": False,
                "validation_errors": ["Could not extract travel details from your query"],
                "error": "No metadata was extracted"
            }
        
        # Log the metadata
        logger.info(f"Extracted metadata: {state.get('metadata')}")
        
        # Step 3: Trip Validator Node
        if spinner:
            spinner.message = "Validating your travel plans"
        logger.info("Step 3: Processing with trip_validator_node")
        state = await trip_validator_node(state)
        
        # Check if trip is valid
        if not state.get('is_valid', False):
            logger.warning(f"Validation failed: {state.get('validation_errors', [])}")
            return state
        
        # Log validation warnings if any
        if "validation_warnings" in state and state["validation_warnings"]:
            logger.info(f"Validation warnings: {state['validation_warnings']}")
        
        # Step 4: Planner Node
        if spinner:
            spinner.message = "Planning your trip components"
        logger.info("Step 4: Processing with planner_node")
        state = await planner_node(state)
        
        # Step 5: Agent Nodes
        nodes_to_call = state.get('nodes_to_call', [])
        logger.info(f"Nodes to call: {nodes_to_call}")
        
        # Initialize selected_flights in state
        state["selected_flights"] = []
        
        # Process initial nodes
        state = await process_nodes(state, nodes_to_call, spinner)
        
        # Step 6: Reviews Node
        if spinner:
            spinner.message = "Analyzing reviews for better recommendations"
        logger.info("Step 6: Processing with reviews_node")
        state = await reviews_node(state)
        
        # Step 7: Summary Node
        if spinner:
            spinner.message = "Generating your personalized itinerary"
        logger.info("Step 7: Processing with summary_node")
        state = await summary_node(state)
        
        logger.info("Initial processing completed successfully")
        
        return state
        
    except Exception as e:
        logger.error(f"Error during travel query processing: {str(e)}")
        return {
            "is_valid": False,
            "validation_errors": [f"An error occurred while processing your request: {str(e)}"],
            "error": str(e)
        }

async def process_feedback(state, feedback, spinner=None):
    """
    Process feedback for an existing itinerary.
    
    Args:
        state: Current state with existing itinerary
        feedback: User feedback dictionary
        spinner: Optional Spinner instance for loading states
        
    Returns:
        Updated state after processing feedback
    """
    try:
        if spinner:
            spinner.message = "Updating your itinerary based on feedback"
        
        # Process feedback
        state = await feedback_parser_node(state, feedback)
        state = await replanning_node(state)
        
        # Rerun necessary nodes
        nodes_to_rerun = state.get("nodes_to_rerun", [])
        state = await process_nodes(state, nodes_to_rerun, spinner)
        
        # Always rerun summary to regenerate itinerary
        if spinner:
            spinner.message = "Generating your updated itinerary"
        state = await summary_node(state)
        
        return state
        
    except Exception as e:
        logger.error(f"Error during feedback processing: {str(e)}")
        return {
            "is_valid": False,
            "validation_errors": [f"An error occurred while processing your feedback: {str(e)}"],
            "error": str(e)
        } 