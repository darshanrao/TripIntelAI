import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import re
from pydantic import ValidationError

# Import enhanced extractors
from app.nodes.enhanced_extractor import (
    enhanced_date_extraction, 
    enhanced_number_extraction,
    enhanced_location_extraction
)

# Import enhanced conversation handler
from app.nodes.enhanced_conversation_handler import ConversationHandler

# Define what fields are required for a valid trip
REQUIRED_FIELDS = {
    "source": "Where will you be starting your trip from?",
    "destination": "What is your destination for this trip?",
    "start_date": "When would you like to start your trip? (Please provide a date in MM/DD/YYYY format)",
    "end_date": "When will your trip end? (Please provide a date in MM/DD/YYYY format)",
    "num_people": "How many people will be traveling?",
}

# Optional fields that enhance the trip experience
OPTIONAL_FIELDS = {
    "preferences": "Do you have any preferences for your trip? (e.g., museums, restaurants, shopping, nature)",
    "budget": "Do you have a budget in mind for this trip?",
    "accommodation_type": "What type of accommodation are you looking for? (e.g., hotel, hostel, rental)",
}

# Initialize the conversation handler
conversation_handler = ConversationHandler()

async def interactive_trip_validator_node(state: Dict[str, Any]) -> Dict[str, Any]:
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
        first_question = await conversation_handler.generate_question("source", type('obj', (object,), {}), [])
        state["next_question"] = first_question
        
        # Record the assistant's question
        conversation_handler.add_to_history("assistant", first_question)
        state["conversation_history"] = conversation_handler.conversation_history
        
        return state
    
    metadata = state["metadata"]
    missing_fields = []
    validation_errors = []
    
    # Check required fields
    for field, prompt in REQUIRED_FIELDS.items():
        value = getattr(metadata, field, None)
        if not value:
            missing_fields.append(field)
            validation_errors.append(f"Missing {field}")
    
    # Validate dates if both are present
    if hasattr(metadata, "start_date") and hasattr(metadata, "end_date") and metadata.start_date and metadata.end_date:
        try:
            # Convert string dates to datetime objects
            start_date = datetime.strptime(metadata.start_date, "%m/%d/%Y")
            end_date = datetime.strptime(metadata.end_date, "%m/%d/%Y")
            
            # Get today's date
            today = datetime.now()
            
            # Check if dates are in the future
            if start_date < today:
                validation_errors.append("Start date must be in the future")
                missing_fields.append("start_date")
            
            # Check if end date is after start date
            if end_date < start_date:
                validation_errors.append("End date must be after start date")
                missing_fields.append("end_date")
                
        except ValueError:
            validation_errors.append("Dates must be in MM/DD/YYYY format")
            if "start_date" not in missing_fields:
                missing_fields.append("start_date")
            if "end_date" not in missing_fields:
                missing_fields.append("end_date")
    
    # Validate num_people if present
    if hasattr(metadata, "num_people") and metadata.num_people:
        try:
            num_people = int(metadata.num_people)
            if num_people <= 0:
                validation_errors.append("Number of people must be greater than 0")
                missing_fields.append("num_people")
        except (ValueError, TypeError):
            validation_errors.append("Number of people must be a valid number")
            missing_fields.append("num_people")
    
    # If we have missing fields, set up the interactive mode
    if missing_fields:
        state["is_valid"] = False
        state["validation_errors"] = validation_errors
        state["missing_fields"] = missing_fields
        state["interactive_mode"] = True
        
        # Track what fields we've already asked about
        previous_fields = [field for field in REQUIRED_FIELDS if field not in missing_fields]
        
        # Determine the next question to ask using the conversational handler
        next_field = missing_fields[0]
        next_question = await conversation_handler.generate_question(next_field, metadata, previous_fields)
        state["next_question"] = next_question
        
        # Record the assistant's question
        conversation_handler.add_to_history("assistant", next_question)
        state["conversation_history"] = conversation_handler.conversation_history
    else:
        # All required fields are present and valid
        state["is_valid"] = True
        state["interactive_mode"] = False
        
        # Add a completion message to the conversation
        completion_message = f"Great! I have all the details I need for your trip to {metadata.destination}."
        conversation_handler.add_to_history("assistant", completion_message)
        state["conversation_history"] = conversation_handler.conversation_history
        
        # Check for optional fields and add suggestions
        suggestions = []
        for field, prompt in OPTIONAL_FIELDS.items():
            value = getattr(metadata, field, None)
            if not value:
                suggestions.append(prompt)
        
        if suggestions:
            state["suggestions"] = suggestions
    
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
                return await interactive_trip_validator_node(state)
            
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
        return await interactive_trip_validator_node(state)
    
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

# Example usage in a chat loop
async def chat_loop_example():
    # Initial state with query but no metadata
    state = {
        "query": "I want to plan a trip",
        "metadata": type('obj', (object,), {
            "source": None,
            "destination": None,
            "start_date": None,
            "end_date": None,
            "num_people": None,
            "preferences": None
        })
    }
    
    # Validate and get first question
    state = await interactive_trip_validator_node(state)
    
    while state.get("interactive_mode") and state.get("missing_fields"):
        print(state["next_question"])
        user_input = input("> ")
        state = await process_user_response(state, user_input)
    
    if state.get("is_valid"):
        print("Great! I have all the information I need.")
        print("Trip details:")
        print(f"- From: {state['metadata'].source}")
        print(f"- To: {state['metadata'].destination}")
        print(f"- Start date: {state['metadata'].start_date}")
        print(f"- End date: {state['metadata'].end_date}")
        print(f"- Number of people: {state['metadata'].num_people}")
        if state['metadata'].preferences:
            print(f"- Preferences: {', '.join(state['metadata'].preferences)}")
    else:
        print("Sorry, I couldn't validate your trip details.")
        print("Errors:", state.get("validation_errors"))

# If running this file directly, demo the chat loop
if __name__ == "__main__":
    asyncio.run(chat_loop_example()) 