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

class GraphState(TypedDict):
    """State for the LangGraph pipeline."""
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
                print("\n" + "="*80)
                print(question)
                print("="*80 + "\n")
                # Get user input
                user_response = input("Your response: ")
                # Update state with user response
                state["user_response"] = user_response
            # Process the response and get updated state
            updated_state = await process_user_response(state, state.get("user_response", ""))
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
        
        # Add edge from process_response back to validator
        workflow.add_edge("process_response", "validator")
        
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
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a travel query through the graph.
        
        Args:
            state: Initial state containing the query
            
        Returns:
            Updated state with results or error
        """
        try:
            # Initialize state for multi-day planning
            state["current_day"] = 1
            state["total_days"] = state.get("metadata", {}).get("duration", 1)
            state["destination"] = state.get("metadata", {}).get("destination", "Unknown")
            state["start_date"] = state.get("metadata", {}).get("start_date", "")
            state["daily_itineraries"] = []
            state["visited_places"] = set()  # Initialize empty set for visited places
            state["visited_restaurants"] = set()  # Initialize empty set for visited restaurants
            state["final_itinerary"] = None  # Initialize final itinerary
            
            # Run the graph using ainvoke for async nodes
            result = await self.graph.ainvoke(state)
            return result
            
        except Exception as e:
            logger.error(f"Error in graph processing: {str(e)}")
            return {
                **state,
                "is_valid": False,
                "error": str(e)
            } 