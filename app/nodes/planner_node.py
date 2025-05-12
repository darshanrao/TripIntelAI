from typing import Dict, Any, List, Literal, Optional, TypedDict
from langchain_anthropic import ChatAnthropic
from app.schemas.trip_schema import TripMetadata

AGENT_SELECTOR_PROMPT = """You are a trip planning assistant. Based on the user's query and travel intent, decide which of the following travel planning nodes to call:

Available nodes:
- "flights": Find flight options for the trip
- "route": Calculate route information if traveling by car/train
- "places": Find attractions and things to do
- "restaurants": Find dining options
- "hotel": Find accommodation options
- "budget": Calculate budget estimates

User query: {query}

Trip metadata:
{metadata}

Decide which nodes to call based on:
1. Explicit user requests (e.g., "Find me hotels in NYC" -> call "hotel")
2. Implicit requirements (e.g., if source and destination are far apart, call "flights")
3. Common needs (most trips need hotels and places to visit)

Return your answer as a list of the node names to call:
E.g., ["flights", "hotel", "places", "restaurants", "budget"]

Do not include any explanation, just return the list of node names.
"""

NodeType = Literal["flights", "route", "places", "restaurants", "hotel", "budget"]

class GraphState(TypedDict):
    """State for the LangGraph pipeline."""
    is_valid: bool
    raw_query: str
    metadata: Optional[TripMetadata]
    error: Optional[str]
    nodes_to_call: List[str]

async def agent_selector_node(state: GraphState) -> GraphState:
    """
    Decide which nodes to call based on user intent.
    
    Args:
        state: Current state containing user query and metadata
        
    Returns:
        Updated state with nodes to call
    """
    # Check if validation passed
    if not state.get("is_valid", False):
        state["nodes_to_call"] = []
        return state
    
    # Get user query and metadata
    user_query = state.get("raw_query", "")
    metadata: Optional[TripMetadata] = state.get("metadata")
    
    if not metadata:
        state["error"] = "No trip metadata available for planning"
        state["nodes_to_call"] = []
        return state
    
    # Initialize LLM
    llm = ChatAnthropic(
        model="claude-3-haiku-20240307",
        temperature=0.2,
        max_tokens=1000
    )
    
    # Use Claude to decide which nodes to call
    response = await llm.ainvoke(
        AGENT_SELECTOR_PROMPT.format(
            query=user_query,
            metadata=metadata.dict()
        )
    )
    
    # Parse the response content
    try:
        import json
        
        # Extract list from the response
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        elif "[" in content and "]" in content:
            content = content[content.find("["):content.rfind("]")+1]
        
        nodes_to_call = json.loads(content)
        
        # Validate node types
        valid_nodes = ["flights", "route", "places", "restaurants", "hotel", "budget"]
        nodes_to_call = [node for node in nodes_to_call if node in valid_nodes]
        
        # Add to state
        state["nodes_to_call"] = nodes_to_call
        
    except Exception as e:
        state["error"] = f"Failed to parse agent selector output: {str(e)}"
        state["nodes_to_call"] = ["flights", "hotel", "places", "budget"]  # Default fallback
    
    return state 