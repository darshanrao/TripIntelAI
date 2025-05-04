from typing import Dict, Any, List, Optional, Callable, TypedDict
from langgraph.graph import Graph, StateGraph
from app.schemas.trip_schema import TripData
from app.nodes.chat_input_node import chat_input_node
# Import mock intent parser instead of the real one
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from mock_intent_parser import mock_intent_parser
from app.nodes.trip_validator_node import trip_validator_node
from app.nodes.planner_node import planner_node
from app.nodes.agent_nodes import (
    flights_node, route_node, places_node, restaurants_node, 
    hotel_node, budget_node
)
from app.nodes.summary_node import summary_node
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GraphState(TypedDict, total=False):
    """State for the LangGraph pipeline."""
    query: str
    raw_query: str
    metadata: Dict[str, Any]
    is_valid: bool
    validation_errors: List[str]
    error: Optional[str]
    nodes_to_call: List[str]
    flights: List[Dict[str, Any]]
    route: Dict[str, Any]
    places: List[Dict[str, Any]]
    restaurants: List[Dict[str, Any]]
    hotel: Dict[str, Any]
    budget: Dict[str, Any]
    itinerary: str

# Define a simple sequential processor function instead of using the graph
async def process_trip_sequentially(query: str) -> Dict[str, Any]:
    """
    Process a trip query in a sequential manner without using a complex LangGraph.
    
    Args:
        query: User's natural language query
        
    Returns:
        Dict containing the final state with the itinerary
    """
    try:
        logger.info(f"Processing query: {query}")
        
        # Initialize initial state with only the query
        state = {"query": query}
        final_state = {}
        
        # Step 1: Chat Input
        logger.info("Step 1: Chat Input Node")
        chat_state = await chat_input_node(state)
        final_state.update(chat_state)
        
        # Step 2: Intent Parser (using mock)
        logger.info("Step 2: Intent Parser Node")
        # Create fresh state with only necessary keys
        intent_input = {"raw_query": final_state["raw_query"], "error": None}
        intent_state = await mock_intent_parser(intent_input)
        
        # Check if metadata is present
        if "metadata" not in intent_state or intent_state["metadata"] is None:
            error_msg = f"Failed to extract metadata from query: {intent_state.get('error', 'Unknown error')}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "is_valid": False,
                "validation_errors": ["Could not understand trip details from your query"]
            }
            
        final_state.update(intent_state)
        
        # Step 3: Validator
        logger.info("Step 3: Trip Validator Node")
        # Create fresh state with only necessary keys
        validator_input = {"metadata": final_state["metadata"], "error": final_state.get("error")}
        validator_state = await trip_validator_node(validator_input)
        final_state.update(validator_state)
        
        # If validation failed, return early
        if not final_state.get("is_valid", False):
            logger.warning(f"Validation failed: {final_state.get('validation_errors', [])}")
            return final_state
        
        # Step 4: Planner
        logger.info("Step 4: Planner Node")
        # Create fresh state with only necessary keys
        planner_input = {
            "raw_query": final_state["raw_query"],
            "metadata": final_state["metadata"],
            "is_valid": final_state["is_valid"],
            "error": final_state.get("error")
        }
        planner_state = await planner_node(planner_input)
        final_state.update(planner_state)
        
        # Step 5: Agent nodes (each node gets a fresh state)
        # Flights node
        logger.info("Step 5a: Flights Node")
        flights_input = {"metadata": final_state["metadata"]}
        flights_state = await flights_node(flights_input)
        final_state["flights"] = flights_state.get("flights", [])
        
        # Places node
        logger.info("Step 5b: Places Node")
        places_input = {"metadata": final_state["metadata"]}
        places_state = await places_node(places_input)
        final_state["places"] = places_state.get("places", [])
        
        # Restaurants node
        logger.info("Step 5c: Restaurants Node") 
        restaurants_input = {"metadata": final_state["metadata"]}
        restaurants_state = await restaurants_node(restaurants_input)
        final_state["restaurants"] = restaurants_state.get("restaurants", [])
        
        # Hotel node
        logger.info("Step 5d: Hotel Node")
        hotel_input = {"metadata": final_state["metadata"]}
        hotel_state = await hotel_node(hotel_input)
        final_state["hotel"] = hotel_state.get("hotel", {})
        
        # Budget node
        logger.info("Step 5e: Budget Node")
        budget_input = {
            "metadata": final_state["metadata"],
            "flights": final_state.get("flights", []),
            "hotel": final_state.get("hotel", {}),
            "places": final_state.get("places", []),
            "route": final_state.get("route", {})
        }
        budget_state = await budget_node(budget_input)
        final_state["budget"] = budget_state.get("budget", {})
        
        # Step 6: Summary
        logger.info("Step 6: Summary Node")
        summary_input = {
            "metadata": final_state["metadata"],
            "flights": final_state.get("flights", []),
            "hotel": final_state.get("hotel", {}),
            "places": final_state.get("places", []),
            "restaurants": final_state.get("restaurants", []),
            "budget": final_state.get("budget", {})
        }
        summary_state = await summary_node(summary_input)
        final_state["itinerary"] = summary_state.get("itinerary", "")
        
        logger.info("Trip processing completed successfully")
        return final_state
        
    except Exception as e:
        error_msg = f"Error processing trip: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return {
            "error": error_msg,
            "is_valid": False,
            "validation_errors": ["An error occurred while processing your request"]
        }

class TripPlannerGraphMock:
    """
    Simplified wrapper that doesn't use the complex LangGraph structure
    to avoid state key conflicts.
    """
    
    async def process(self, query: str) -> Dict[str, Any]:
        """
        Process a user query and return the final state.
        
        Args:
            query: User's natural language query
            
        Returns:
            Dict containing the final state with the itinerary
        """
        return await process_trip_sequentially(query) 