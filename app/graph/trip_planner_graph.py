from typing import Dict, Any, TypedDict, Optional, List, Set
from langgraph.graph import StateGraph
from app.nodes.chat_input_node import chat_input_node
from app.nodes.intent_parser_node import intent_parser_node
from app.nodes.trip_validator_node import trip_validator_node, process_user_response
from app.nodes.planner_node import agent_selector_node
from app.nodes.agents.flights_node import flights_node
from app.nodes.agents.places_node import places_node, fetch_attractions, fetch_restaurants
from app.nodes.agents.reviews_node import reviews_node
from app.nodes.agents.budget_node import budget_node
from app.nodes.agents.route_node import route_node
from app.nodes.agents.itinerary_planner_node import itinerary_planner_node
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
        workflow.add_node("agent_selector", agent_selector_node)
        
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
        workflow.add_node("itinerary_planner", itinerary_planner_node)
        
        # Add fetch attractions and restaurants nodes
        workflow.add_node("fetch_attractions", fetch_attractions)
        workflow.add_node("fetch_restaurants", fetch_restaurants)
        
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
        
        # Add sequential edges for attractions and restaurants flow
        workflow.add_edge("flights_agent", "fetch_attractions")  # First get attractions
        workflow.add_edge("fetch_attractions", "fetch_restaurants")  # Then get restaurants
        workflow.add_edge("fetch_restaurants", "reviews_agent")
        workflow.add_edge("reviews_agent", "budget_agent")
        
        # Add conditional edge from places_agent to either reviews_agent or itinerary_planner
        workflow.add_conditional_edges(
            "places_agent",
            lambda x: "reviews_agent" if x.get("place_type") == "attraction" else "itinerary_planner",
            {
                "reviews_agent": "reviews_agent",
                "itinerary_planner": "itinerary_planner"
            }
        )
        
        # Add conditional edge from itinerary_planner to either places_agent (for next day) or final_merge
        workflow.add_conditional_edges(
            "itinerary_planner",
            lambda x: "places_agent" if x.get("current_day", 0) < x.get("total_days", 0) else "final_merge",
            {
                "places_agent": "places_agent",
                "final_merge": "final_merge"
            }
        )
        
        # Add final merge node (non-AI merge of all daily itineraries)
        async def final_merge(state):
            # Get flights from the state
            flights = state.get("flights", [])
            arrival_flight = None
            departure_flight = None
            
            if flights:
                # Find arrival and departure flights by flight_type
                for flight in flights:
                    if flight.get("flight_type") == "arrival":
                        arrival_flight = flight
                    elif flight.get("flight_type") == "departure":
                        departure_flight = flight
            
            # Merge all daily itineraries into final itinerary
            final_itinerary = {
                "trip_summary": state.get("metadata", {}),
                "daily_itineraries": state.get("daily_itineraries", []),
                "total_cost": sum(day.get("total_cost", 0) for day in state.get("daily_itineraries", [])),
                "total_days": state.get("total_days", 0),
                "unique_places_visited": len(state.get("visited_places", set())),
                "unique_restaurants_visited": len(state.get("visited_restaurants", set())),
                "arrival_flight": {
                    "id": arrival_flight.get("id") if arrival_flight else None,
                    "airline": arrival_flight.get("airline") if arrival_flight else None,
                    "flight_number": arrival_flight.get("flight_number") if arrival_flight else None,
                    "departure_airport": arrival_flight.get("departure_airport") if arrival_flight else None,
                    "departure_city": arrival_flight.get("departure_city") if arrival_flight else None,
                    "arrival_airport": arrival_flight.get("arrival_airport") if arrival_flight else None,
                    "arrival_city": arrival_flight.get("arrival_city") if arrival_flight else None,
                    "departure_time": arrival_flight.get("departure_time") if arrival_flight else None,
                    "arrival_time": arrival_flight.get("arrival_time") if arrival_flight else None,
                    "price": arrival_flight.get("price") if arrival_flight else None,
                    "duration_minutes": arrival_flight.get("duration_minutes") if arrival_flight else None,
                    "stops": arrival_flight.get("stops") if arrival_flight else None,
                    "aircraft": arrival_flight.get("aircraft") if arrival_flight else None,
                    "cabin_class": arrival_flight.get("cabin_class") if arrival_flight else None,
                    "baggage_included": arrival_flight.get("baggage_included") if arrival_flight else None
                },
                "departure_flight": {
                    "id": departure_flight.get("id") if departure_flight else None,
                    "airline": departure_flight.get("airline") if departure_flight else None,
                    "flight_number": departure_flight.get("flight_number") if departure_flight else None,
                    "departure_airport": departure_flight.get("departure_airport") if departure_flight else None,
                    "departure_city": departure_flight.get("departure_city") if departure_flight else None,
                    "arrival_airport": departure_flight.get("arrival_airport") if departure_flight else None,
                    "arrival_city": departure_flight.get("arrival_city") if departure_flight else None,
                    "departure_time": departure_flight.get("departure_time") if departure_flight else None,
                    "arrival_time": departure_flight.get("arrival_time") if departure_flight else None,
                    "price": departure_flight.get("price") if departure_flight else None,
                    "duration_minutes": departure_flight.get("duration_minutes") if departure_flight else None,
                    "stops": departure_flight.get("stops") if departure_flight else None,
                    "aircraft": departure_flight.get("aircraft") if departure_flight else None,
                    "cabin_class": departure_flight.get("cabin_class") if departure_flight else None,
                    "baggage_included": departure_flight.get("baggage_included") if departure_flight else None
                }
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