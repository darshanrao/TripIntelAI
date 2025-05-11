from typing import Dict, Any, List, Optional
from app.utils.logger import logger
from app.utils.anthropic_client import anthropic_client

class MissingInfoHandler:
    """Handles missing information collection using ReAct pattern."""
    
    REQUIRED_FIELDS = {
        "source": "Where are you traveling from?",
        "destination": "Where would you like to go?",
        "start_date": "When would you like to start your trip?",
        "end_date": "When would you like to end your trip?",
        "num_people": "How many people are traveling?"
    }
    
    def __init__(self):
        self.date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'\d{2}-\d{2}-\d{4}',  # DD-MM-YYYY
            r'\d{2}\.\d{2}\.\d{4}' # DD.MM.YYYY
        ]
        
        self.number_patterns = [
            r'\d+',  # Simple number
            r'one|two|three|four|five|six|seven|eight|nine|ten'  # Written numbers
        ]
    
    def get_missing_fields(self, metadata: Dict[str, Any]) -> List[str]:
        """Identify which required fields are missing from the metadata."""
        missing = []
        for field in self.REQUIRED_FIELDS:
            if not metadata.get(field):
                missing.append(field)
        return missing
    
    def generate_question(self, field: str) -> str:
        """Generate a question for the missing field."""
        return self.REQUIRED_FIELDS.get(field, f"Please provide {field}")
    
    def parse_date(self, text: str) -> Optional[str]:
        """Parse various date formats into YYYY-MM-DD."""
        import re
        from datetime import datetime
        
        for pattern in self.date_patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group()
                try:
                    # Try different date formats
                    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y', '%d.%m.%Y']:
                        try:
                            date = datetime.strptime(date_str, fmt)
                            return date.strftime('%Y-%m-%d')
                        except ValueError:
                            continue
                except Exception:
                    continue
        return None
    
    def parse_number(self, text: str) -> Optional[int]:
        """Parse numbers from text."""
        import re
        
        # Try simple number first
        match = re.search(r'\d+', text)
        if match:
            return int(match.group())
        
        # Try written numbers
        number_map = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
        }
        
        for word, num in number_map.items():
            if word in text.lower():
                return num
        
        return None
    
    def parse_location(self, text: str) -> Optional[str]:
        """Parse location names from text."""
        # This is a simple implementation - could be enhanced with NLP
        return text.strip() if text.strip() else None

async def missing_info_handler_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle missing information collection using ReAct pattern.
    
    Args:
        state: Current state containing metadata and user response
        
    Returns:
        Updated state with new information
    """
    handler = MissingInfoHandler()
    metadata = state.get("metadata", {})
    
    # If we have a user response, process it
    if "user_response" in state:
        response = state["user_response"]
        current_question = state.get("next_question", "")
        
        # Determine which field we're asking about
        field = None
        for f, q in handler.REQUIRED_FIELDS.items():
            if q in current_question:
                field = f
                break
        
        if field:
            # Parse the response based on field type
            if field in ["start_date", "end_date"]:
                value = handler.parse_date(response)
            elif field == "num_people":
                value = handler.parse_number(response)
            else:  # source or destination
                value = handler.parse_location(response)
            
            if value:
                metadata[field] = value
                state["metadata"] = metadata
                logger.info(f"Updated {field} with value: {value}")
            else:
                logger.warning(f"Could not parse {field} from response: {response}")
    
    # Check for remaining missing fields
    missing_fields = handler.get_missing_fields(metadata)
    
    if missing_fields:
        # Generate next question
        next_field = missing_fields[0]
        state["next_question"] = handler.generate_question(next_field)
        state["thought"] = f"Need to collect information about {next_field}"
        state["is_valid"] = False
    else:
        state["is_valid"] = True
        state["next_question"] = None
        state["thought"] = "All required information has been collected"
    
    return state 