from typing import Dict, Any, List, TypedDict, Optional
from langchain_anthropic import ChatAnthropic
from datetime import datetime
from app.schemas.trip_schema import TripMetadata
import json
import re
import os
import asyncio
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

INTENT_PARSER_PROMPT = '''You are a travel intent parser. Extract structured travel intent from the user's query that may contain typos or natural language variations.

User Query: {query}

Extract the following information if present:
- Source location (where the trip starts from)
- Destination location (where the trip goes to)
- Start date of the trip
- End date of the trip
- Number of people traveling
- Preferences (e.g., budget, luxury, family-friendly, restaurants, museums, etc.)

When extracting locations:
- Correct common typos (e.g., "bsoton" → "Boston", "NYC" → "New York City")
- Default source to "Unknown" if not specified

When extracting dates:
- Recognize various formats (e.g., "May 18th", "05/18/2025", "next month")
- Convert to YYYY-MM-DD format
- Handle typos in month names (e.g., "mmay" → "May")
- If only one date is mentioned, assume a 3-day trip
- If no year is specified, assume the next available date (not in the past)

If any information is missing, make a reasonable guess or use null.
Format dates as YYYY-MM-DD.

Return the output as a JSON object with these fields:
- source: string or null
- destination: string or null
- start_date: YYYY-MM-DD string or null
- end_date: YYYY-MM-DD string or null
- num_people: integer or 1 if not specified
- preferences: array of strings or empty array

IMPORTANT: Return ONLY the JSON object without any explanations, markdown, or additional text. No explanation before or after.

Example response:
{{"source":"Boston","destination":"New York City","start_date":"2025-05-15","end_date":"2025-05-18","num_people":2,"preferences":["budget","restaurants"]}}
'''

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
    logger.info(f"Attempting to extract JSON from text: {text[:100]}...")
    
    # Try to find JSON between curly braces
    json_match = re.search(r'(\{.*\})', text, re.DOTALL)
    
    if json_match:
        try:
            # Parse the JSON
            json_str = json_match.group(1)
            logger.info(f"Found JSON pattern: {json_str[:100]}...")
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSONDecodeError with curly brace pattern: {str(e)}")
    
    # Try to find JSON in code blocks
    code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if code_block_match:
        try:
            json_str = code_block_match.group(1)
            logger.info(f"Found JSON in code block: {json_str[:100]}...")
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSONDecodeError with code block pattern: {str(e)}")
    
    # Try to parse the whole text as JSON
    try:
        logger.info("Trying to parse entire text as JSON")
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"JSONDecodeError parsing whole text: {str(e)}")
    
    # Try a more aggressive approach to find any JSON-like structure
    try:
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            json_str = text[start_idx:end_idx+1]
            logger.info(f"Aggressive JSON extraction found: {json_str[:100]}...")
            return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"JSONDecodeError with aggressive extraction: {str(e)}")
    
    logger.error("Failed to extract any valid JSON from the response")
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
    
    logger.info(f"Processing user query: '{user_query}'")
    
    if not user_query:
        logger.error("No user query provided")
        state["error"] = "No user query provided"
        return state
    
    # Initialize LLM
    try:
        # Use direct Anthropic client instead of langchain wrapper for testing
        from anthropic import Anthropic
        
        # Get API key from environment
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            state["error"] = "ANTHROPIC_API_KEY not found in environment variables"
            return state
        
        client = Anthropic(api_key=api_key)
        logger.info("Successfully initialized Anthropic client directly")
        
        # Format the prompt
        prompt = INTENT_PARSER_PROMPT.format(query=user_query)
        
        # Use direct API call
        try:
            logger.info("Calling Claude API directly")
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                temperature=0,
                system="You extract travel information and return it as valid JSON.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Get content from response
            content = response.content[0].text
            logger.info(f"Received raw response from Claude: {content[:150]}...")
            
            # Extract JSON
            intent_data = extract_json_from_llm_response(content)
            
            if not intent_data:
                logger.error("Failed to extract valid JSON from Claude's response")
                state["error"] = "Failed to parse intent: Invalid JSON format in response"
                return state
            
            logger.info(f"Successfully parsed intent data: {intent_data}")
            
            # Convert date strings to datetime objects if present
            try:
                if intent_data.get("start_date"):
                    logger.info(f"Converting start_date: {intent_data['start_date']}")
                    try:
                        intent_data["start_date"] = datetime.fromisoformat(intent_data["start_date"])
                        logger.info(f"Converted start_date to: {intent_data['start_date']}")
                    except ValueError as e:
                        logger.error(f"Error converting start_date: {str(e)}")
                        # Try to parse in another format
                        try:
                            from dateutil import parser
                            intent_data["start_date"] = parser.parse(intent_data["start_date"])
                            logger.info(f"Converted start_date using dateutil to: {intent_data['start_date']}")
                        except Exception as e2:
                            logger.error(f"Failed to parse start_date with dateutil: {str(e2)}")
                            # Keep as string if it's still there
                            if isinstance(intent_data.get("start_date"), str):
                                logger.info("Keeping start_date as string")
                            else:
                                intent_data["start_date"] = None
                
                if intent_data.get("end_date"):
                    logger.info(f"Converting end_date: {intent_data['end_date']}")
                    try:
                        intent_data["end_date"] = datetime.fromisoformat(intent_data["end_date"])
                        logger.info(f"Converted end_date to: {intent_data['end_date']}")
                    except ValueError as e:
                        logger.error(f"Error converting end_date: {str(e)}")
                        # Try to parse in another format
                        try:
                            from dateutil import parser
                            intent_data["end_date"] = parser.parse(intent_data["end_date"])
                            logger.info(f"Converted end_date using dateutil to: {intent_data['end_date']}")
                        except Exception as e2:
                            logger.error(f"Failed to parse end_date with dateutil: {str(e2)}")
                            # Keep as string if it's still there
                            if isinstance(intent_data.get("end_date"), str):
                                logger.info("Keeping end_date as string")
                            else:
                                intent_data["end_date"] = None
                
                # Create a TripMetadata instance
                logger.info("Creating TripMetadata instance")
                trip_metadata = TripMetadata(
                    source=intent_data.get("source", "Unknown"),
                    destination=intent_data.get("destination", "Unknown"),
                    start_date=intent_data.get("start_date", None),
                    end_date=intent_data.get("end_date", None),
                    num_people=intent_data.get("num_people", 1),
                    preferences=intent_data.get("preferences", [])
                )
                
                logger.info(f"Created TripMetadata: {trip_metadata}")
                
                # Add to state
                state["metadata"] = trip_metadata
                logger.info("Successfully added metadata to state")
                
            except Exception as e:
                logger.error(f"Error processing intent data: {str(e)}")
                logger.error(traceback.format_exc())
                state["error"] = f"Failed to process intent data: {str(e)}"
            
        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            logger.error(traceback.format_exc())
            state["error"] = f"Failed to call Claude API: {str(e)}"
            return state
        
    except Exception as e:
        logger.error(f"Error in LLM processing: {str(e)}")
        logger.error(traceback.format_exc())
        state["error"] = f"Failed to parse intent: {str(e)}"
    
    return state

async def test_claude_json():
    # Initialize Claude
    from anthropic import Anthropic
    
    # Get API key from environment
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not found in environment variables")
        return
    
    client = Anthropic(api_key=api_key)
    
    # Simple prompt
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        temperature=0,
        system="Return ONLY valid JSON.",
        messages=[
            {"role": "user", "content": "Return this exact JSON: {\"test\": \"success\"}"}
        ]
    )
    
    print("Raw response:", response.content[0].text)

if __name__ == "__main__":
    asyncio.run(test_claude_json()) 