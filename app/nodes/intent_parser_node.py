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
from app.utils.anthropic_client import get_anthropic_client
from app.utils.logger import logger

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
- Return null for source if not specified

When extracting dates:
- Recognize various formats (e.g., "May 18th", "05/18/2025", "next month")
- Convert to YYYY-MM-DD format
- Handle typos in month names (e.g., "mmay" → "May")
- Return null for any missing dates
- Do not make assumptions about trip duration

If any information is missing, return null for that field.
Format dates as YYYY-MM-DD.

Return the output as a JSON object with these fields:
- source: string or null
- destination: string or null
- start_date: YYYY-MM-DD string or null
- end_date: YYYY-MM-DD string or null
- num_people: integer or null
- preferences: array of strings or empty array

IMPORTANT: Return ONLY the JSON object without any explanations, markdown, or additional text. No explanation before or after.

Example response:
{{"source":null,"destination":"New York City","start_date":null,"end_date":null,"num_people":null,"preferences":[]}}
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

async def intent_parser_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse the user's intent and extract trip metadata using Claude.
    
    Args:
        state: Current state containing the user's query
        
    Returns:
        Updated state with extracted metadata
    """
    try:
        query = state.get("query")
        if not query:
            logger.error("No query found in state")
            return {
                **state,
                "error": "No query provided",
                "is_valid": False
            }
            
        logger.info(f"Processing user query: '{state}'")
        
        # Initialize Anthropic client
        client = get_anthropic_client()
        logger.info("Successfully initialized Anthropic client directly")
        
        # Create prompt for Claude
        prompt = f"""
        You are a travel planning assistant. Extract travel information from this query:
        "{query}"
        
        Extract the following information:
        - source (departure city/country)
        - destination (arrival city/country)
        - start_date (in YYYY-MM-DD format)
        - end_date (in YYYY-MM-DD format)
        - num_people (as an integer)
        - preferences (list of interests/requirements)
        
        Return ONLY a JSON object with these fields. Use null for missing values.
        Example format:
        {{
            "source": "New York",
            "destination": "Paris",
            "start_date": "2024-05-15",
            "end_date": "2024-05-22",
            "num_people": 2,
            "preferences": ["museums", "food"]
        }}
        """
        
        logger.info("Calling Claude API directly")
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        # Extract the response text - properly handle the Message object
        response_text = response.content[0].text
        if not response_text:
            raise ValueError("Empty response from Claude")
            
        logger.info(f"Received raw response from Claude: {response_text[:100]}...")
        
        # Parse the JSON response
        try:
            logger.info(f"Attempting to extract JSON from text: {response_text[:100]}...")
            # Find JSON pattern in the response
            json_pattern = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_pattern:
                json_str = json_pattern.group(0)
                logger.info(f"Found JSON pattern: {json_str[:100]}...")
                intent_data = json.loads(json_str)
            else:
                raise ValueError("No JSON object found in response")
                
            logger.info(f"Successfully parsed intent data: {intent_data}")
            
            # Ensure preferences is a list
            if intent_data.get("preferences") is None:
                intent_data["preferences"] = []
            
            # Create TripMetadata instance
            logger.info("Creating TripMetadata instance")
            metadata = TripMetadata(**intent_data)
            
            # Update state with metadata
            return {
                **state,
                "metadata": metadata,
                "is_valid": True
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from response: {str(e)}")
            return {
                **state,
                "error": f"Failed to parse response: {str(e)}",
                "is_valid": False
            }
            
    except Exception as e:
        logger.error(f"Error in intent parser: {str(e)}")
        return {
            **state,
            "error": str(e),
            "is_valid": False
        }

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