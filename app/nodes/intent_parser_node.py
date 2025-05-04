from typing import Dict, Any, List, TypedDict, Optional
from langchain_anthropic import ChatAnthropic
from datetime import datetime
from app.schemas.trip_schema import TripMetadata
import json
import re
import os
import asyncio

INTENT_PARSER_PROMPT = """You are a travel intent parser. Extract structured travel intent from the user's query.

User Query: {query}

Extract the following information if present:
- Source location (where the trip starts)
- Destination location (where the trip goes to)
- Start date of the trip
- End date of the trip
- Number of people traveling
- Preferences (e.g., budget, luxury, family-friendly, restaurants, museums, etc.)

If any information is missing, make a reasonable guess or use None.
Format dates as YYYY-MM-DD.

Return the output as a JSON object with these fields:
- source: string or null
- destination: string or null
- start_date: YYYY-MM-DD string or null
- end_date: YYYY-MM-DD string or null
- num_people: integer or 1 if not specified
- preferences: array of strings or empty array

IMPORTANT: Return ONLY the JSON object without any explanations, markdown, or additional text. The response should start with '{' and end with '}'.

Example response:
{"source":"Boston","destination":"New York City","start_date":"2025-05-15","end_date":"2025-05-18","num_people":2,"preferences":["budget","restaurants"]}
"""

class GraphState(TypedDict):
    """State for the LangGraph pipeline."""
    raw_query: str
    metadata: Optional[TripMetadata]
    error: Optional[str]

def extract_json_from_llm_response(text):
    """
    Extract JSON from an LLM response, handling various formats.
    
    Args:
        text: Raw text from LLM
        
    Returns:
        Parsed JSON object or None if parsing fails
    """
    # Try to find JSON between curly braces
    json_match = re.search(r'(\{.*\})', text, re.DOTALL)
    
    if json_match:
        try:
            # Parse the JSON
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON in code blocks
    code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to parse the whole text as JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    return None

async def intent_parser_node(state: GraphState) -> GraphState:
    """
    Extract structured travel intent from user query.
    
    Args:
        state: Current state containing the user's query
        
    Returns:
        Updated state with extracted intent
    """
    # Get the user query
    user_query = state.get("raw_query", "")
    
    if not user_query:
        state["error"] = "No user query provided"
        return state
    
    # Initialize LLM
    llm = ChatAnthropic(
        model="claude-3-haiku-20240307",
        temperature=0.2,
        max_tokens=1000
    )
    
    # Use Claude to extract intent
    try:
        response = await llm.ainvoke(
            INTENT_PARSER_PROMPT.format(query=user_query)
        )
        
        # Parse the response content (expecting JSON)
        content = response.content
        
        # Extract JSON from the response
        intent_data = extract_json_from_llm_response(content)
        
        if not intent_data:
            state["error"] = "Failed to parse intent: Invalid JSON format in response"
            return state
        
        # Convert date strings to datetime objects if present
        try:
            if intent_data.get("start_date"):
                intent_data["start_date"] = datetime.fromisoformat(intent_data["start_date"])
            
            if intent_data.get("end_date"):
                intent_data["end_date"] = datetime.fromisoformat(intent_data["end_date"])
            
            # Create a TripMetadata instancexx
            trip_metadata = TripMetadata(
                source=intent_data.get("source", ""),
                destination=intent_data.get("destination", ""),
                start_date=intent_data.get("start_date", None),
                end_date=intent_data.get("end_date", None),
                num_people=intent_data.get("num_people", 1),
                preferences=intent_data.get("preferences", [])
            )
            
            # Add to state
            state["metadata"] = trip_metadata
            
        except Exception as e:
            state["error"] = f"Failed to process intent data: {str(e)}"
        
    except Exception as e:
        state["error"] = f"Failed to parse intent: {str(e)}"
    
    return state

async def test_claude_json():
    # Initialize Claude
    llm = ChatAnthropic(
        model="claude-3-haiku-20240307",
        temperature=0.2,
        max_tokens=1000
    )
    
    # Simple prompt
    response = await llm.ainvoke(
        "Return this exact JSON: {\"test\": \"success\"}"
    )
    
    print("Raw response:", response.content)

if __name__ == "__main__":
    asyncio.run(test_claude_json()) 