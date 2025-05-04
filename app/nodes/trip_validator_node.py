from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime, timedelta
import re
from app.schemas.trip_schema import TripMetadata

# Import enhanced extractors for interactive mode
from app.nodes.enhanced_extractor import (
    enhanced_date_extraction, 
    enhanced_number_extraction,
    enhanced_location_extraction
)

# Import enhanced conversation handler for interactive mode
from app.nodes.enhanced_conversation_handler import ConversationHandler

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

# Define what fields are required for a valid trip
REQUIRED_FIELDS = {
    "destination": "What is your destination for this trip?",
}

# Define fields that should have defaults if missing
DEFAULT_FIELDS = {
    "source": "Unknown",
    "num_people": 1,
}

# Optional fields that enhance the trip experience
OPTIONAL_FIELDS = {
    "preferences": "Do you have any preferences for your trip? (e.g., museums, restaurants, shopping, nature)",
    "budget": "Do you have a budget in mind for this trip?",
    "accommodation_type": "What type of accommodation are you looking for? (e.g., hotel, hostel, rental)",
}

# Initialize the conversation handler for interactive mode
conversation_handler = ConversationHandler()

async def trip_validator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate trip parameters from the metadata.
    
    This validator supports two modes:
    1. Standard validation: Just validates the metadata and returns validation status
    2. Interactive validation: When interactive_mode=True is set in the state, it will
       generate questions for missing fields and handle user responses conversationally
    
    Args:
        state: Current state containing trip metadata
        
    Returns:
        Updated state with validation status
    """
    # Check if interactive mode is requested
    if state.get("interactive_mode", False) and "query" in state:
        return await _interactive_trip_validator_node(state)
    
    # Standard validation mode
    # Extract metadata
    metadata: Optional[TripMetadata] = state.get("metadata")
    
    if not metadata:
        state["error"] = "No trip metadata available for validation"
        state["is_valid"] = False
        return state
    
    # Initialize validation
    errors = []
    warnings = []
    
    # Apply default values for missing but non-required fields
    for field, default_value in DEFAULT_FIELDS.items():
        if not getattr(metadata, field, None):
            setattr(metadata, field, default_value)
            warnings.append(f"Using default value for {field}: {default_value}")
    
    # Validate destination (the only strictly required field)
    if not metadata.destination:
        errors.append("Destination location is required")
    
    # Set default dates if missing
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if not metadata.start_date:
        # Default to starting 7 days from now
        default_start = today + timedelta(days=7)
        metadata.start_date = default_start
        warnings.append(f"Using default start date: {default_start.strftime('%Y-%m-%d')}")
    
    if not metadata.end_date:
        # Default to ending 3 days after start date
        if metadata.start_date:
            default_end = metadata.start_date + timedelta(days=3)
            metadata.end_date = default_end
            warnings.append(f"Using default end date: {default_end.strftime('%Y-%m-%d')}")
    
    # Perform soft validation on dates (warnings only)
    if isinstance(metadata.start_date, datetime) and metadata.start_date < today:
        warnings.append("Start date is in the past, but we'll proceed with planning")
    
    # Validate date order and duration
    if metadata.start_date and metadata.end_date:
        if isinstance(metadata.end_date, datetime) and isinstance(metadata.start_date, datetime) and metadata.end_date < metadata.start_date:
            # Swap dates if end is before start
            metadata.start_date, metadata.end_date = metadata.end_date, metadata.start_date
            warnings.append("End date was before start date, dates have been swapped")
        
        # Calculate duration if both dates are datetime objects
        if isinstance(metadata.end_date, datetime) and isinstance(metadata.start_date, datetime):
            duration = (metadata.end_date - metadata.start_date).days
            if duration > 14:
                warnings.append("Trip duration exceeds 14 days, which is unusually long")
            
            # Add duration to state
            state["trip_duration"] = duration
    
    # Validate number of people
    if metadata.num_people < 1:
        metadata.num_people = 1
        warnings.append("Number of people reset to 1 (minimum value)")
    
    # Add warnings to state
    state["validation_warnings"] = warnings
    
    # Update state with validation results
    state["validation_errors"] = errors
    state["is_valid"] = len(errors) == 0
    
    # Keep the metadata with applied defaults
    state["metadata"] = metadata
    
    return state

# Interactive validation functions below

async def _interactive_trip_validator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Interactive trip validator that checks for required fields and asks
    the user for any missing information in a conversational way.
    
    Args:
        state: The current state object containing query and metadata
        
    Returns:
        Updated state with is_valid flag, any validation errors, and 
        potentially enhanced metadata from user interaction
    """
    # Initialize conversation history if not present
    if "conversation_history" not in state:
        state["conversation_history"] = []
    
    # Record the initial query if it's the first interaction
    if len(state["conversation_history"]) == 0 and "query" in state:
        conversation_handler.add_to_history("user", state["query"])
        state["conversation_history"] = conversation_handler.conversation_history
    
    # Check if we already have metadata from previous parsing
    if "metadata" not in state or not state["metadata"]:
        state["is_valid"] = False
        state["validation_errors"] = ["No trip metadata found. Please provide trip details."]
        state["missing_fields"] = list(REQUIRED_FIELDS.keys())
        state["interactive_mode"] = True
        
        # Generate conversational first question
        first_question = await conversation_handler.generate_question("destination", type('obj', (object,), {}), [])
        state["next_question"] = first_question
        
        # Record the assistant's question
        conversation_handler.add_to_history("assistant", first_question)
        state["conversation_history"] = conversation_handler.conversation_history
        
        return state
    
    metadata = state["metadata"]
    missing_fields = []
    validation_errors = []
    
    # Check required fields - only destination is strictly required
    if not getattr(metadata, "destination", None):
        missing_fields.append("destination")
        validation_errors.append("Missing destination")
    
    # Apply defaults for missing non-required fields
    for field, default_value in DEFAULT_FIELDS.items():
        if not getattr(metadata, field, None):
            setattr(metadata, field, default_value)
    
    # If dates are missing, prompt for them but don't block validation
    if not hasattr(metadata, "start_date") or not metadata.start_date:
        # We won't add this to missing_fields to not block validation
        # But we'll ask for it if interactive mode is on
        if state.get("interactive_mode", False) and "destination" not in missing_fields:
            missing_fields.append("start_date")
    
    if not hasattr(metadata, "end_date") or not metadata.end_date:
        # Similarly, end_date is nice to have but not required
        if state.get("interactive_mode", False) and "destination" not in missing_fields and "start_date" not in missing_fields:
            missing_fields.append("end_date")
    
    # Update state based on validation results
    if missing_fields and state.get("interactive_mode", False):
        state["is_valid"] = False
        state["missing_fields"] = missing_fields
        
        # Generate next question for first missing field
        field_to_ask = missing_fields[0]
        next_question = await conversation_handler.generate_question(field_to_ask, metadata, validation_errors)
        state["next_question"] = next_question
        
        # Record the assistant's question
        conversation_handler.add_to_history("assistant", next_question)
        state["conversation_history"] = conversation_handler.conversation_history
    else:
        # All required fields are present
        state["is_valid"] = True
        state["missing_fields"] = []
        state["next_question"] = None
    
    return state

async def process_user_response(state: Dict[str, Any], user_response: str) -> Dict[str, Any]:
    """
    Process a user's response to a question and update the state accordingly.
    
    Args:
        state: Current state with missing_fields and metadata
        user_response: The user's text response to the question
        
    Returns:
        Updated state with the user's response integrated
    """
    if not state.get("interactive_mode") or not state.get("missing_fields"):
        # Not in interactive mode or no missing fields to process
        return state
    
    # Record the user's response
    conversation_handler.add_to_history("user", user_response)
    state["conversation_history"] = conversation_handler.conversation_history
    
    missing_fields = state["missing_fields"]
    current_field = missing_fields[0]
    metadata = state["metadata"]
    
    # Check if the user's response indicates flexibility
    is_flexible = await conversation_handler.is_flexible_response(user_response)
    
    if is_flexible:
        # Handle the flexible response
        flexibility_result = await conversation_handler.handle_flexible_response(
            current_field, user_response, metadata
        )
        
        if flexibility_result["is_flexible"]:
            # Use the suggested value
            if current_field == "source":
                metadata.source = flexibility_result["suggested_value"]
            elif current_field == "destination":
                metadata.destination = flexibility_result["suggested_value"]
            elif current_field == "start_date":
                metadata.start_date = flexibility_result["suggested_value"]
            elif current_field == "end_date":
                metadata.end_date = flexibility_result["suggested_value"]
            elif current_field == "num_people":
                metadata.num_people = flexibility_result["suggested_value"]
            elif current_field == "preferences":
                metadata.preferences = flexibility_result["suggested_value"]
            
            # Add an explanation to the conversation
            explanation = flexibility_result["explanation"]
            conversation_handler.add_to_history("assistant", explanation)
            state["conversation_history"] = conversation_handler.conversation_history
            
            # Remove the processed field from missing_fields
            missing_fields.pop(0)
            
            # Update the state
            state["metadata"] = metadata
            state["missing_fields"] = missing_fields
            
            # If there are still missing fields, prepare the next question
            if missing_fields:
                next_field = missing_fields[0]
                previous_fields = [field for field in REQUIRED_FIELDS if field not in missing_fields and field != next_field]
                next_question = await conversation_handler.generate_question(next_field, metadata, previous_fields)
                
                state["next_question"] = next_question
                
                # Record the assistant's question
                conversation_handler.add_to_history("assistant", next_question)
                state["conversation_history"] = conversation_handler.conversation_history
            else:
                # All required fields have been provided, re-validate
                return await _interactive_trip_validator_node(state)
            
            return state
    
    # Process the response based on the field type (for non-flexible responses)
    if current_field == "source":
        # Try enhanced location extraction first
        location = await enhanced_location_extraction(user_response, "source")
        if location:
            metadata.source = location
        else:
            # Fall back to basic extraction
            metadata.source = user_response.strip()
    
    elif current_field == "destination":
        # Try enhanced location extraction first
        location = await enhanced_location_extraction(user_response, "destination")
        if location:
            metadata.destination = location
        else:
            # Fall back to basic extraction
            metadata.destination = user_response.strip()
    
    elif current_field == "start_date":
        # Create context for date extraction
        context = {}
        if hasattr(metadata, "destination") and metadata.destination:
            context["destination"] = metadata.destination
        
        # Try enhanced date extraction first
        date = await enhanced_date_extraction(user_response, "start_date", context)
        if date:
            metadata.start_date = date
        else:
            # Fall back to regex pattern matching
            date = _extract_date(user_response)
            if date:
                metadata.start_date = date
            else:
                # Keep this field in missing_fields and inform the user
                return _create_date_error_response(state, "start_date")
    
    elif current_field == "end_date":
        # Create context for date extraction
        context = {}
        if hasattr(metadata, "destination") and metadata.destination:
            context["destination"] = metadata.destination
        if hasattr(metadata, "start_date") and metadata.start_date:
            context["start_date"] = metadata.start_date
        
        # Try enhanced date extraction first
        date = await enhanced_date_extraction(user_response, "end_date", context)
        if date:
            metadata.end_date = date
        else:
            # Fall back to regex pattern matching
            date = _extract_date(user_response)
            if date:
                metadata.end_date = date
            else:
                # Keep this field in missing_fields and inform the user
                return _create_date_error_response(state, "end_date")
    
    elif current_field == "num_people":
        # Try enhanced number extraction first
        num = await enhanced_number_extraction(user_response)
        if num:
            metadata.num_people = num
        else:
            # Fall back to basic extraction
            num = _extract_number(user_response)
            if num:
                metadata.num_people = num
            else:
                # Keep this field in missing_fields and inform the user
                error_msg = "I need a valid number of travelers. How many people will be on this trip?"
                conversation_handler.add_to_history("assistant", error_msg)
                state["conversation_history"] = conversation_handler.conversation_history
                return {
                    **state,
                    "next_question": error_msg
                }
    
    elif current_field == "preferences":
        # Extract preferences as a list
        prefs = [p.strip() for p in user_response.split(',')]
        metadata.preferences = prefs
    
    # Remove the processed field from missing_fields
    missing_fields.pop(0)
    
    # Update the state
    state["metadata"] = metadata
    state["missing_fields"] = missing_fields
    
    # Add an acknowledgment to the conversation if a field was successfully processed
    if len(conversation_handler.response_variety["acknowledgments"]) > 0:
        import random
        ack = random.choice(conversation_handler.response_variety["acknowledgments"])
        conversation_handler.add_to_history("assistant", ack)
    
    # If there are still missing fields, prepare the next question
    if missing_fields:
        next_field = missing_fields[0]
        previous_fields = [field for field in REQUIRED_FIELDS if field not in missing_fields and field != next_field]
        next_question = await conversation_handler.generate_question(next_field, metadata, previous_fields)
        
        state["next_question"] = next_question
        
        # Record the assistant's question
        conversation_handler.add_to_history("assistant", next_question)
        state["conversation_history"] = conversation_handler.conversation_history
    else:
        # All required fields have been provided, re-validate
        return await _interactive_trip_validator_node(state)
    
    return state

def _extract_date(text: str) -> Optional[str]:
    """Extract a date from text and return in MM/DD/YYYY format."""
    # Try direct MM/DD/YYYY format
    pattern1 = r'(\d{1,2})/(\d{1,2})/(\d{4})'
    match = re.search(pattern1, text)
    if match:
        month, day, year = match.groups()
        return f"{int(month):02d}/{int(day):02d}/{year}"
    
    # Try YYYY-MM-DD format
    pattern2 = r'(\d{4})-(\d{1,2})-(\d{1,2})'
    match = re.search(pattern2, text)
    if match:
        year, month, day = match.groups()
        return f"{int(month):02d}/{int(day):02d}/{year}"
    
    # Try text month like "May 15, 2025" or "May 15 2025"
    pattern3 = r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2})(?:,|\s+)?\s*(\d{4})'
    match = re.search(pattern3, text, re.IGNORECASE)
    if match:
        month_str, day, year = match.groups()
        month_map = {
            "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
            "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
            "aug": 8, "august": 8, "sep": 9, "september": 9, "oct": 10, "october": 10,
            "nov": 11, "november": 11, "dec": 12, "december": 12
        }
        month = month_map.get(month_str.lower(), 1)
        return f"{month:02d}/{int(day):02d}/{year}"
    
    # Try relative dates like "next week", "in 3 days"
    if "tomorrow" in text.lower():
        tomorrow = datetime.now() + timedelta(days=1)
        return tomorrow.strftime("%m/%d/%Y")
    
    if "next week" in text.lower():
        next_week = datetime.now() + timedelta(weeks=1)
        return next_week.strftime("%m/%d/%Y")
    
    if "next month" in text.lower():
        next_month = datetime.now() + timedelta(days=30)
        return next_month.strftime("%m/%d/%Y")
    
    # Try to match "in X days/weeks/months"
    pattern4 = r'in\s+(\d+)\s+(day|days|week|weeks|month|months)'
    match = re.search(pattern4, text.lower())
    if match:
        num, unit = match.groups()
        num = int(num)
        if 'day' in unit:
            future = datetime.now() + timedelta(days=num)
        elif 'week' in unit:
            future = datetime.now() + timedelta(weeks=num)
        else:  # months
            future = datetime.now() + timedelta(days=num*30)
        return future.strftime("%m/%d/%Y")
    
    return None

def _extract_number(text: str) -> Optional[int]:
    """Extract a number from text."""
    # Direct number
    pattern1 = r'\b(\d+)\b'
    match = re.search(pattern1, text)
    if match:
        return int(match.group(1))
    
    # Text numbers
    text_numbers = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
        'a couple': 2, 'a few': 3, 'several': 4
    }
    
    for text_num, value in text_numbers.items():
        if text_num in text.lower():
            return value
    
    return None

def _create_date_error_response(state: Dict[str, Any], date_field: str) -> Dict[str, Any]:
    """Create a response for date parsing errors."""
    field_name = "start date" if date_field == "start_date" else "end date"
    error_msg = f"I couldn't understand that date format. Could you please provide the {field_name} again? You can use formats like MM/DD/YYYY or month names like 'May 15, 2025'."
    
    # Record the error in the conversation history
    conversation_handler.add_to_history("assistant", error_msg)
    state["conversation_history"] = conversation_handler.conversation_history
    
    return {
        **state,
        "next_question": error_msg
    } 