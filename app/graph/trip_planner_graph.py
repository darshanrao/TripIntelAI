from typing import Dict, Any, TypedDict, Optional
from langgraph.graph import StateGraph
from app.nodes.chat_input_node import chat_input_node
from app.nodes.intent_parser_node import intent_parser_node
from app.nodes.trip_validator_node import trip_validator_node, process_user_response
from app.nodes.planner_node import planner_node
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
        workflow.add_node("planner", planner_node)
        
        # Add edges
        workflow.add_edge("chat_input", "intent_parser")
        workflow.add_edge("intent_parser", "validator")
        
        # Add conditional edges for validation and stop condition
        workflow.add_conditional_edges(
            "validator",
            lambda x: "planner" if x.get("is_valid") else "process_response",
            {
                "process_response": "process_response",
                "planner": "planner"
            }
        )
        
        # Add edge from process_response back to validator
        workflow.add_edge("process_response", "validator")
        
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