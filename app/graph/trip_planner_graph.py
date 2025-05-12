from typing import Dict, Any, TypedDict, Optional, List, Set
from langgraph.graph import StateGraph
from app.nodes.chat_input_node import chat_input_node
from app.nodes.intent_parser_node import intent_parser_node
from app.nodes.trip_validator_node import trip_validator_node, process_user_response
from app.nodes.planner_node import planner_node
from app.nodes.agents.flights_node import flights_node
from app.nodes.agents.places_node import places_node
from app.nodes.agents.reviews_node import reviews_node
from app.nodes.agents.budget_node import budget_node
from app.nodes.agents.route_node import route_node
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
    nodes_to_call: List[str]
    flights: List[Dict[str, Any]]  # Will contain arrival and departure flights
    places: List[Dict[str, Any]]
    restaurants: List[Dict[str, Any]]
    hotel: Dict[str, Any]
    budget: Dict[str, Any]
    route: Dict[str, Any]
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
        workflow.add_node("places_agent", places_node)
        workflow.add_node("reviews_agent", reviews_node)
        workflow.add_node("budget_agent", budget_node)
        workflow.add_node("route_agent", route_node)
        workflow.add_node("planner_agent", planner_node)
        
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
        
        # Add sequential edges for initial data gathering
        workflow.add_edge("flights_agent", "places_agent")
        workflow.add_edge("places_agent", "reviews_agent")
        workflow.add_edge("reviews_agent", "route_agent")
        workflow.add_edge("route_agent", "budget_agent")
        workflow.add_edge("budget_agent", "planner_agent")
        
        # Add conditional edge from planner to either next day or final merge
        workflow.add_conditional_edges(
            "planner_agent",
            lambda x: "planner_agent" if x.get("current_day", 0) < x.get("total_days", 0) else "final_merge",
            {
                "planner_agent": "planner_agent",
                "final_merge": "final_merge"
            }
        )
        
        # Add final merge node (non-AI merge of all daily itineraries)
        async def final_merge(state):
            # Merge all daily itineraries into final itinerary
            final_itinerary = {
                "trip_summary": state.get("metadata", {}),
                "daily_itineraries": state.get("daily_itineraries", []),
                "total_cost": sum(day.get("total_cost", 0) for day in state.get("daily_itineraries", [])),
                "total_days": state.get("total_days", 0),
                "unique_places_visited": len(state.get("visited_places", set())),
                "unique_restaurants_visited": len(state.get("visited_restaurants", set()))
            }
            state["final_itinerary"] = final_itinerary
            return state
            
        workflow.add_node("final_merge", final_merge)
        
        # Set entry point
        workflow.set_entry_point("chat_input")
        
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
            state["daily_itineraries"] = []
            state["visited_places"] = set()  # Initialize empty set for visited places
            state["visited_restaurants"] = set()  # Initialize empty set for visited restaurants
            
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