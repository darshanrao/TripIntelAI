from typing import Dict, Any, List, Optional, Callable, TypedDict
from langgraph.graph import Graph, StateGraph
from app.schemas.trip_schema import TripData
from app.nodes.chat_input_node import chat_input_node
from app.nodes.intent_parser_node import intent_parser_node
from app.nodes.trip_validator_node import trip_validator_node
from app.nodes.planner_node import planner_node
from app.nodes.agent_nodes import (
    flights_node, route_node, places_node, restaurants_node, 
    hotel_node, budget_node, reviews_node
)
from app.nodes.flight_selection_node import flight_selection_node
from app.nodes.summary_node import summary_node

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
    selected_flights: List[Dict[str, Any]]
    route: Dict[str, Any]
    places: List[Dict[str, Any]]
    restaurants: List[Dict[str, Any]]
    hotel: Dict[str, Any]
    budget: Dict[str, Any]
    itinerary: str

class TripPlannerGraph:
    """
    Main LangGraph workflow for the AI Travel Planner.
    Orchestrates all the nodes and defines the execution flow.
    """
    
    def _should_continue_after_validation(self, state: Dict[str, Any]) -> str:
        """
        Decision function to determine if we should continue after validation.
        
        Args:
            state: Current state
            
        Returns:
            Next node to call
        """
        if state.get("is_valid", False):
            return "planner"
        else:
            return "end"
    
    def _routes_based_on_planner(self, state: Dict[str, Any]) -> List[str]:
        """
        Determine which agent nodes to call based on planner output.
        
        Args:
            state: Current state containing nodes_to_call
            
        Returns:
            List of nodes to call
        """
        nodes_to_call = state.get("nodes_to_call", [])
        return nodes_to_call
    
    def build(self) -> Graph:
        """
        Build the LangGraph pipeline for trip planning.
        
        The complete pipeline includes:
        - ChatInputNode
        - IntentParserNode
        - TripValidatorNode
        - PlannerNode
        - Agent nodes (Flights, Route, Places, Restaurants, Hotel, Budget)
        - ReviewsNode
        - SummaryNode
        """
        # Initialize the graph
        workflow = StateGraph(GraphState)
        
        # Add nodes using function-based approach
        workflow.add_node("chat_input", chat_input_node)
        workflow.add_node("intent_parser", intent_parser_node)
        workflow.add_node("validator", trip_validator_node)
        workflow.add_node("planner", planner_node)
        
        # Add agent nodes
        workflow.add_node("flights", flights_node)
        workflow.add_node("flight_selection", flight_selection_node)
        workflow.add_node("route", route_node)
        workflow.add_node("places", places_node)
        workflow.add_node("restaurants", restaurants_node)
        workflow.add_node("hotel", hotel_node)
        workflow.add_node("budget", budget_node)
        
        # Add reviews node
        workflow.add_node("reviews", reviews_node)
        
        # Add summary node
        workflow.add_node("summary", summary_node)
        
        # Add end node (for validation failures)
        workflow.add_node("end", lambda x: x)
        
        # Define the edges between nodes
        workflow.set_entry_point("chat_input")
        
        # Main workflow sequence
        workflow.add_edge("chat_input", "intent_parser")
        workflow.add_edge("intent_parser", "validator")
        
        # Conditional edge after validation
        workflow.add_conditional_edges(
            "validator",
            self._should_continue_after_validation,
            {
                "planner": "planner",
                "end": "end"
            }
        )
        
        # Dynamic routing based on planner output
        for node_name in ["flights", "route", "places", "restaurants", "hotel", "budget"]:
            if node_name == "flights":
                workflow.add_conditional_edges(
                    "planner",
                    lambda state, node=node_name: node if node in state.get("nodes_to_call", []) else None,
                    {
                        node_name: node_name,
                        None: "reviews"
                    }
                )
                workflow.add_edge("flights", "flight_selection")
                workflow.add_edge("flight_selection", "reviews")
            else:
                workflow.add_conditional_edges(
                    "planner",
                    lambda state, node=node_name: node if node in state.get("nodes_to_call", []) else None,
                    {
                        node_name: node_name,
                        None: "reviews"
                    }
                )
                workflow.add_edge(node_name, "reviews")
        
        # After reviews, go to summary
        workflow.add_edge("reviews", "summary")
        
        # Set the final state
        workflow.set_finish_point("summary")
        workflow.set_finish_point("end")
        
        return workflow.compile()
    
    def _is_plan_complete(self, state: Dict[str, Any]) -> bool:
        """
        Check if all planned nodes have been executed.
        
        Args:
            state: Current state
            
        Returns:
            True if all planned nodes have been executed
        """
        nodes_to_call = state.get("nodes_to_call", [])
        executed_nodes = set()
        
        # Check which nodes have data in the state
        if "flights" in state and state["flights"]:
            executed_nodes.add("flights")
        if "route" in state and state["route"]:
            executed_nodes.add("route")
        if "places" in state and state["places"]:
            executed_nodes.add("places")
        if "restaurants" in state and state["restaurants"]:
            executed_nodes.add("restaurants")
        if "hotel" in state and state["hotel"]:
            executed_nodes.add("hotel")
        if "budget" in state and state["budget"]:
            executed_nodes.add("budget")
        
        # Check if all planned nodes have been executed
        return all(node in executed_nodes for node in nodes_to_call)

    async def process(self, query: str) -> Dict[str, Any]:
        """
        Process a user query through the graph and return the final itinerary.
        
        Args:
            query: User's natural language query
            
        Returns:
            Dict containing the generated itinerary
        """
        graph = self.build()
        
        # Initialize state with user query, ensuring no conflicting keys exist
        initial_state = {
            "query": query,
            "raw_query": query,
            # Explicitly initialize empty values for agent node keys to avoid conflicts
            "flights": [],
            "selected_flights": [],
            "route": {},
            "places": [],
            "restaurants": [],
            "hotel": {},
            "budget": {}
        }
        
        try:
            # Run the graph
            final_state = await graph.ainvoke(initial_state)
            return final_state
        except Exception as e:
            # Handle errors gracefully
            print(f"[ERROR] Error processing query in trip planner graph: {e}")
            return {
                "error": str(e),
                "response": "Sorry, I had trouble processing your travel request. Could you please try again with more details?"
            }
    
    async def process_with_trip_data(self, trip_data: TripData) -> Dict[str, Any]:
        """
        Process trip data through the graph and return the final itinerary.
        Used for testing or bypassing the intent parsing step.
        
        Args:
            trip_data: The validated trip data
            
        Returns:
            Dict containing the generated itinerary
        """
        # Create initial state with trip data
        initial_state = {
            "metadata": trip_data.metadata.dict(),
            "flights": [f.dict() for f in trip_data.flights],
            "hotel": trip_data.hotel.dict() if trip_data.hotel else {},
            "places": [p.dict() for p in trip_data.places],
            "restaurants": [r.dict() for r in trip_data.restaurants],
            "budget": trip_data.budget.dict() if trip_data.budget else {},
            "route": {}  # Initialize route key to avoid conflicts
        }
        
        try:
            # Process directly through the summary node
            result_state = await summary_node(initial_state)
            return result_state
        except Exception as e:
            # Handle errors gracefully
            print(f"[ERROR] Error processing trip data in summary node: {e}")
            return {
                "error": str(e),
                "response": "Sorry, I had trouble processing your travel data. Please check your trip details and try again."
            }

    async def process_with_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process with an existing state through the graph and return the final result.
        
        Args:
            state: Current state with validated metadata
            
        Returns:
            Dict containing the generated itinerary and other results
        """
        graph = self.build()
        
        # Ensure the state has all necessary keys to avoid conflicts
        for key in ["flights", "route", "places", "restaurants", "hotel", "budget"]:
            if key not in state:
                if key in ["route", "hotel", "budget"]:
                    state[key] = {}
                else:
                    state[key] = []
        
        try:
            # Run the graph with the existing state
            final_state = await graph.ainvoke(state)
            return final_state
        except Exception as e:
            # Handle errors gracefully
            print(f"[ERROR] Error processing state in trip planner graph: {e}")
            return {
                "error": str(e),
                "response": "Sorry, I had trouble processing your travel request. Could you please try again with more details?"
            } 