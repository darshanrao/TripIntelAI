from typing import Dict, Any, TypedDict, Optional, List, Set
from langgraph.graph import StateGraph, END
from app.nodes.chat_input_node import chat_input_node
from app.nodes.intent_parser_node import intent_parser_node
from app.nodes.trip_validator_node import trip_validator_node, process_user_response
from app.nodes.planner_node import agent_selector_node
from app.nodes.agents.flights_node import flights_node
from app.nodes.agents.places_node import fetch_attractions, fetch_restaurants
from app.nodes.agents.itinerary_planner_node import itinerary_planner_node
from app.nodes.agents.hotel_node import hotel_node
from app.utils.logger import logger
from supabase import create_client, Client
import os
import json
import uuid

class GraphState(TypedDict):
    """State for the LangGraph pipeline."""
    session_id: str  # Add session_id to track state
    query: str
    raw_query: str
    metadata: Dict[str, Any]
    is_valid: bool
    next_question: Optional[str]
    error: Optional[str]
    thought: Optional[str]
    action: Optional[str]
    action_input: Optional[Dict[str, Any]]
    observation: Optional[str]
    user_response: Optional[str]
    current_day: int  # Track which day we're planning
    total_days: int   # Total number of days in the trip
    destination: str  # Destination city/location
    start_date: str   # Start date of the trip
    nodes_to_call: List[str]
    flights: List[Dict[str, Any]]  # Will contain arrival and departure flights
    places: List[Dict[str, Any]]
    restaurants: List[Dict[str, Any]]
    hotel: Dict[str, Any]
    daily_itineraries: List[Dict[str, Any]]  # Store itineraries for each day
    final_itinerary: Optional[Dict[str, Any]]  # Final merged itinerary
    visited_places: Set[str]  # Track places that have been added to the itinerary
    visited_restaurants: Set[str]  # Track restaurants that have been added to the itinerary

class TripPlannerGraph:
    """
    Main LangGraph workflow for the AI Travel Planner.
    Orchestrates the core nodes and defines the execution flow.
    """
    
    def __init__(self):
        """Initialize the trip planner graph."""
        self.graph = self._build()
        # Initialize Supabase client
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
    
    def _build(self) -> StateGraph:
        """
        Build the trip planner graph with core nodes.
        
        Returns:
            StateGraph: The configured graph
        """
        # Create the graph with state schema
        workflow = StateGraph(state_schema=GraphState)
        
        # Add core nodes
        workflow.add_node("chat_input", chat_input_node)
        workflow.add_node("intent_parser", intent_parser_node)
        workflow.add_node("validator", trip_validator_node)
        workflow.add_node("agent_selector", agent_selector_node)
        
        # Add end node
        async def end_node(state):
            """End node that returns the final state."""
            return state
        workflow.add_node("end", end_node)
        
        # Create an async wrapper for process_user_response
        async def process_response_wrapper(state):
            # Get the question from state
            question = state.get("next_question")
            if question:
                # Save the state before asking the user
                await self.save_state(state)
                print("\n" + "="*80)
                print(question)
                print("="*80 + "\n")
                # Get user input
                user_response = input("Your response: ")
                # Update state with user response
                state["user_response"] = user_response
            # Process the response and get updated state
            updated_state = await process_user_response(state, state.get("user_response", ""))
            # Save the state after processing response
            await self.save_state(updated_state)
            # Return the complete updated state
            return updated_state
            
        workflow.add_node("process_response", process_response_wrapper)
        
        # Add agent nodes
        workflow.add_node("flights_agent", flights_node)
        workflow.add_node("hotels_agent", hotel_node)
        workflow.add_node("attractions_agent", fetch_attractions)
        workflow.add_node("restaurants_agent", fetch_restaurants)
        workflow.add_node("itinerary_planner", itinerary_planner_node)
        
        # Add edges
        workflow.add_edge("chat_input", "intent_parser")
        workflow.add_edge("intent_parser", "validator")
        
        # Add conditional edges for validation and stop condition
        workflow.add_conditional_edges(
            "validator",
            lambda x: "flights_agent" if x.get("is_valid") else "process_response",
            {
                "process_response": "process_response",
                "flights_agent": "flights_agent"
            }
        )
        
        # Add edge from process_response to agent_selector instead of back to validator
        workflow.add_edge("process_response", "agent_selector")
        
        # Add edge from agent_selector to validator
        workflow.add_edge("agent_selector", "validator")
        
        # Add sequential edges for the new flow
        workflow.add_edge("flights_agent", "hotels_agent")  # First get flights, then hotels
        workflow.add_edge("hotels_agent", "attractions_agent")  # Then get attractions
        workflow.add_edge("attractions_agent", "restaurants_agent")  # Then get restaurants
        workflow.add_edge("restaurants_agent", "itinerary_planner")  # Then plan itinerary
        
        # Add conditional edge for daily planning
        def should_continue(state: GraphState) -> str:
            """Determine if we should continue planning or end."""
            if state["current_day"] < state["total_days"]:
                return "itinerary_planner"
            return "end"
        
        workflow.add_conditional_edges(
            "itinerary_planner",
            should_continue
        )
        
        # Set entry and end points
        workflow.set_entry_point("chat_input")
        workflow.set_finish_point("end")
        
        # Compile the graph
        return workflow.compile()
    
    async def save_state(self, state: Dict[str, Any]) -> None:
        """Save the current state to Supabase."""
        try:
            # Convert sets to lists for JSON serialization
            state_to_save = {
                **state,
                "visited_places": list(state.get("visited_places", set())),
                "visited_restaurants": list(state.get("visited_restaurants", set()))
            }
            
            # Convert TripMetadata to dict if present
            if "metadata" in state_to_save and hasattr(state_to_save["metadata"], "model_dump"):
                state_to_save["metadata"] = state_to_save["metadata"].model_dump()
            
            logger.info(f"Saving state for session {state['session_id']}")
            logger.debug(f"State content: {json.dumps(state_to_save, indent=2)}")
            
            # Save to Supabase
            self.supabase.table("trip_states").upsert({
                "session_id": state["session_id"],
                "state": json.dumps(state_to_save),
                "updated_at": "now()"
            }).execute()
            
            logger.info("State saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving state to Supabase: {str(e)}")
            raise
    
    async def load_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load the state from Supabase."""
        try:
            logger.info(f"Loading state for session {session_id}")
            
            response = self.supabase.table("trip_states")\
                .select("state")\
                .eq("session_id", session_id)\
                .order("updated_at", desc=True)\
                .limit(1)\
                .execute()
            
            if response.data and len(response.data) > 0:
                state_data = response.data[0]["state"]
                if isinstance(state_data, str):
                    state = json.loads(state_data)
                else:
                    state = state_data
                # Recursively convert sets to lists
                state = self._convert_sets_to_lists(state)
                logger.info("State loaded successfully")
                logger.debug(f"Loaded state: {json.dumps(state, indent=2)}")
                return state
            logger.info("No existing state found")
            return None
            
        except Exception as e:
            logger.error(f"Error loading state from Supabase: {str(e)}")
            return None

    def _convert_sets_to_lists(self, obj):
        """Recursively convert sets to lists in the given object."""
        if isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_sets_to_lists(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_sets_to_lists(item) for item in obj]
        else:
            return obj
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a travel query through the graph.
        
        Args:
            state: Initial state containing the query
            
        Returns:
            Updated state with results or error
        """
        try:
            # Generate or use existing session_id
            if "session_id" not in state:
                state["session_id"] = str(uuid.uuid4())
            
            # Load existing state if available
            existing_state = await self.load_state(state["session_id"])
            if existing_state:
                state = {**existing_state, **state}
            
            # Initialize state for multi-day planning
            state["current_day"] = 1
            state["total_days"] = state.get("metadata", {}).get("duration", 1)
            state["destination"] = state.get("metadata", {}).get("destination", "Unknown")
            state["start_date"] = state.get("metadata", {}).get("start_date", "")
            state["daily_itineraries"] = []
            state["visited_places"] = set()
            state["visited_restaurants"] = set()
            state["final_itinerary"] = None
            
            # Run the graph
            result = await self.graph.ainvoke(state)
            
            # Save the updated state
            await self.save_state(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in graph processing: {str(e)}")
            return {
                **state,
                "is_valid": False,
                "error": str(e)
            } 