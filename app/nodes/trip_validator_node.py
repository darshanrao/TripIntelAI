from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime, timedelta
import re
from app.schemas.trip_schema import TripMetadata
from app.nodes.missing_info_handler_node import missing_info_handler_node
import json
from app.utils.anthropic_client import anthropic_client, get_anthropic_client
from app.utils.logger import logger

class GraphState(TypedDict):
    """State for the LangGraph pipeline."""
    metadata: Optional[TripMetadata]
    error: Optional[str]
    is_valid: bool
    validation_errors: List[str]
    trip_duration: Optional[int]
    # Interactive mode fields
    interactive_mode: Optional[bool]
    missing_fields: Optional[List[str]]
    next_question: Optional[str]
    conversation_history: Optional[List[Dict[str, Any]]]
    # ReAct specific fields
    thought: Optional[str]
    action: Optional[str]
    action_input: Optional[Dict[str, Any]]
    observation: Optional[str]

# Define what fields are required for a valid trip
REQUIRED_FIELDS = {
    "destination": "What is your destination for this trip?",
    "preferences": "What are your preferences for this trip? (e.g., museums, restaurants, shopping, nature)"
}

# Define fields that should have defaults if missing
DEFAULT_FIELDS = {
    "source": "Unknown",
    "num_people": 1,
}

# Optional fields that enhance the trip experience
OPTIONAL_FIELDS = {
    "budget": "Do you have a budget in mind for this trip?",
    "accommodation_type": "What type of accommodation are you looking for? (e.g., hotel, hostel, rental)",
}

async def trip_validator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates trip metadata and collects missing information using ReAct pattern.
    Follows a step-by-step approach to collect each missing field.
    
    Args:
        state: Current state containing metadata and validation status
        
    Returns:
        Updated state with validation results and next question
    """
    try:
        # Initialize ReAct fields if not present
        if "thought" not in state:
            state["thought"] = None
        if "action" not in state:
            state["action"] = None
        if "action_input" not in state:
            state["action_input"] = None
        if "observation" not in state:
            state["observation"] = None
            
        # Get metadata from state
        metadata = state.get("metadata")
        logger.info("=== Validator Node ===")
        logger.info(f"Current metadata: {metadata}")
        
        if not metadata:
            logger.error("No metadata found in state")
            return {
                **state,
                "thought": "No trip metadata found. Need to start collecting information.",
                "action": "collect_info",
                "action_input": {"field": "source"},
                "next_question": "Where will you be traveling from?",
                "is_valid": False
            }
        
        # Convert metadata to dict if it's a TripMetadata object
        if isinstance(metadata, TripMetadata):
            metadata_dict = metadata.dict()
        else:
            metadata_dict = metadata
            
        # Define required fields and their questions
        required_fields = {
            "source": "Where will you be traveling from?",
            "start_date": "When would you like to start your trip?",
            "end_date": "When would you like to end your trip?",
            "num_people": "How many people will be traveling?",
            "preferences": "What are your preferences for this trip? (e.g., museums, restaurants, shopping, nature)"
        }
        
        # Check which fields are missing
        missing_fields = []
        for field, question in required_fields.items():
            if field == "preferences":
                # For preferences, check if it's None or empty list
                if metadata_dict.get(field) is None or (isinstance(metadata_dict.get(field), list) and len(metadata_dict.get(field)) == 0):
                    missing_fields.append(field)
            elif not metadata_dict.get(field):
                missing_fields.append(field)
                
        # If all fields are present, mark as valid
        if not missing_fields:
            logger.info("All required fields present")
            return {
                **state,
                "thought": "All required information is present.",
                "action": "complete",
                "action_input": {},
                "is_valid": True
            }
            
        # Get the next field to ask about
        next_field = missing_fields[0]
        
        # Generate a contextual question using Claude
        client = get_anthropic_client()
        prompt = f"""
        You are a helpful travel planning assistant. The user is planning a trip to {metadata_dict.get('destination', 'an unspecified location')}.
        
        Current trip information:
        {metadata_dict}
        
        Missing information:
        {', '.join(missing_fields)}
        
        Generate a natural, conversational question to ask about the next missing field: {next_field}
        
        Guidelines:
        1. Be friendly and conversational
        2. Consider any existing information we have
        3. Be specific about what information we need
        4. If asking about dates, suggest common formats
        5. If asking about number of people, make it clear we need a specific number
        
        Just return the question text, nothing else.
        """
        
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=100,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        question = response.content[0].text.strip()
        logger.info(f"Generated question for {next_field}: {question}")
        
        return {
            **state,
            "thought": f"Need to collect information about {next_field}",
            "action": "collect_info",
            "action_input": {"field": next_field},
            "next_question": question,
            "is_valid": False
        }
        
    except Exception as e:
        logger.error(f"Error in trip validator: {str(e)}")
        return {
            **state,
            "thought": f"Error occurred: {str(e)}",
            "action": "error",
            "action_input": {"error": str(e)},
            "is_valid": False
        }

async def process_user_response(state: Dict[str, Any], user_response: str) -> Dict[str, Any]:
    """
    Process user's response using Claude to extract and validate information.
    Uses ReAct pattern to reason about the response and update state.
    
    Args:
        state: Current state with metadata and validation status
        user_response: User's text response to the question
        
    Returns:
        Updated state with extracted and validated information
    """
    try:
        # Create a new state to ensure immutability
        new_state = state.copy()
        
        # Get the current field we're collecting
        current_field = new_state.get("action_input", {}).get("field")
        if not current_field:
            return new_state
            
        # Get metadata
        metadata = new_state.get("metadata", {})
        logger.info("=== Process User Response ===")
        logger.info(f"Processing response for field: {current_field}")
        logger.info(f"User response: {user_response}")
        logger.info(f"Current metadata before processing: {metadata}")
        
        if isinstance(metadata, TripMetadata):
            metadata_dict = metadata.dict()
        else:
            metadata_dict = metadata.copy()
            
        # Use Claude to analyze the response with specialized prompts
        client = get_anthropic_client()
        
        # Define specialized prompts for different field types
        prompts = {
            "preferences": f"""
            You are a travel planning assistant analyzing a user's preferences.
            
            Current trip information: {metadata_dict}
            User's response about preferences: {user_response}
            
            Extract specific, actionable preferences that would help in planning activities.
            For example:
            - If user says "I love trying new foods and exploring local markets", extract ["food exploration", "local markets"]
            - If user says "I enjoy art museums and historical sites", extract ["art museums", "historical sites"]
            - If user says "I want to experience the local culture and nightlife", extract ["local culture", "nightlife"]
            
            Return your analysis in JSON format:
            {{
                "extracted_value": ["list", "of", "specific", "preferences"],
                "confidence": "high/medium/low",
                "reasoning": "Your reasoning about the extraction",
                "validation_errors": ["Any validation errors found"]
            }}
            """,
            
            "start_date": f"""
            You are a travel planning assistant analyzing a user's response about travel dates.
            
            Current trip information: {metadata_dict}
            User's response about start date: {user_response}
            
            Extract the start date, handling various date formats and relative dates:
            - Absolute dates: "May 15th", "15th of May", "05/15"
            - Relative dates: "next month", "in 2 weeks", "tomorrow"
            - Ranges: "sometime in May", "early next month"
            
            Return your analysis in JSON format:
            {{
                "extracted_value": "YYYY-MM-DD",
                "confidence": "high/medium/low",
                "reasoning": "Your reasoning about the extraction",
                "validation_errors": ["Any validation errors found"]
            }}
            """,
            
            "end_date": f"""
            You are a travel planning assistant analyzing a user's response about travel dates.
            
            Current trip information: {metadata_dict}
            User's response about end date: {user_response}
            
            Extract the end date, handling various date formats and relative dates:
            - Absolute dates: "May 20th", "20th of May", "05/20"
            - Relative dates: "next month", "in 2 weeks", "tomorrow"
            - Ranges: "sometime in May", "early next month"
            - Duration: "for 5 days", "for a week"
            
            Return your analysis in JSON format:
            {{
                "extracted_value": "YYYY-MM-DD",
                "confidence": "high/medium/low",
                "reasoning": "Your reasoning about the extraction",
                "validation_errors": ["Any validation errors found"]
            }}
            """,
            
            "source": f"""
            You are a travel planning assistant analyzing a user's response about their departure location.
            
            Current trip information: {metadata_dict}
            User's response about source location: {user_response}
            
            Extract the departure city/location, handling various formats:
            - City names: "New York", "NYC", "New York City"
            - Airports: "JFK", "LaGuardia"
            - Regions: "New York area", "NY metro"
            
            Return your analysis in JSON format:
            {{
                "extracted_value": "standardized city name",
                "confidence": "high/medium/low",
                "reasoning": "Your reasoning about the extraction",
                "validation_errors": ["Any validation errors found"]
            }}
            """,
            
            "destination": f"""
            You are a travel planning assistant analyzing a user's response about their destination.
            
            Current trip information: {metadata_dict}
            User's response about destination: {user_response}
            
            Extract the destination city/location, handling various formats:
            - City names: "Paris", "City of Light"
            - Regions: "Paris region", "Île-de-France"
            - Landmarks: "Eiffel Tower area", "Louvre district"
            
            Return your analysis in JSON format:
            {{
                "extracted_value": "standardized city name",
                "confidence": "high/medium/low",
                "reasoning": "Your reasoning about the extraction",
                "validation_errors": ["Any validation errors found"]
            }}
            """,
            
            "num_people": f"""
            You are a travel planning assistant analyzing a user's response about the number of travelers.
            
            Current trip information: {metadata_dict}
            User's response about number of people: {user_response}
            
            Extract the number of travelers, handling various formats:
            - Direct numbers: "2", "two", "2 people"
            - Groups: "my family", "me and my partner", "a group of 4"
            
            Return your analysis in JSON format:
            {{
                "extracted_value": integer_number,
                "confidence": "high/medium/low",
                "reasoning": "Your reasoning about the extraction",
                "validation_errors": ["Any validation errors found"]
            }}
            """
        }
        
        # Get the appropriate prompt for the current field
        prompt = prompts.get(current_field, f"""
            You are a travel planning assistant analyzing a user's response.
            
            Current field being collected: {current_field}
            Current trip information: {metadata_dict}
            User's response: {user_response}
            
            Extract the relevant information for the {current_field} field.
            
            Return your analysis in JSON format:
            {{
                "extracted_value": "The value extracted from the response",
                "confidence": "high/medium/low",
                "reasoning": "Your reasoning about the extraction",
                "validation_errors": ["Any validation errors found"]
            }}
        """)
        
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        # Parse the response - properly handle the Message object
        response_text = response.content[0].text
        if not response_text:
            raise ValueError("Empty response from Claude")
            
        try:
            analysis = json.loads(response_text)
        except json.JSONDecodeError:
            logger.error("Failed to parse Claude's response as JSON")
            return {
                **new_state,
                "thought": "Failed to parse response analysis",
                "action": "error",
                "action_input": {"error": "Invalid response format"},
                "is_valid": False
            }
            
        # Update metadata with extracted value if confidence is high
        if analysis["confidence"] == "high" or current_field == "preferences":
            # For preferences, ensure we have a list
            if current_field == "preferences":
                if isinstance(analysis["extracted_value"], str):
                    # If it's a string, split it into a list
                    analysis["extracted_value"] = [x.strip() for x in analysis["extracted_value"].split(",")]
                elif not isinstance(analysis["extracted_value"], list):
                    analysis["extracted_value"] = [analysis["extracted_value"]]
            
            # Update metadata dictionary
            metadata_dict[current_field] = analysis["extracted_value"]
            
            # Create new metadata object
            if isinstance(metadata, TripMetadata):
                new_metadata = TripMetadata(**metadata_dict)
            else:
                new_metadata = metadata_dict
                
            logger.info(f"Updated metadata after processing: {new_metadata}")
            
            # Update state with new metadata
            new_state["metadata"] = new_metadata
            new_state["thought"] = analysis["reasoning"]
            new_state["action"] = "update_metadata"
            new_state["action_input"] = {"field": current_field, "value": analysis["extracted_value"]}
            new_state["is_valid"] = False
            
            return new_state
        else:
            # If confidence is low, ask for clarification
            new_state["thought"] = analysis["reasoning"]
            new_state["action"] = "ask_clarification"
            new_state["action_input"] = {"field": current_field, "errors": analysis["validation_errors"]}
            new_state["next_question"] = f"I'm not sure I understood your response about {current_field}. Could you please clarify?"
            new_state["is_valid"] = False
            
            return new_state
            
    except Exception as e:
        logger.error(f"Error processing user response: {str(e)}")
        return {
            **new_state,
            "thought": f"Error occurred: {str(e)}",
            "action": "error",
            "action_input": {"error": str(e)},
            "is_valid": False
        }
