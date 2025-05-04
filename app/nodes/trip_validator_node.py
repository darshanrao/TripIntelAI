from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime, timedelta
from app.schemas.trip_schema import TripMetadata

class GraphState(TypedDict):
    """State for the LangGraph pipeline."""
    metadata: Optional[TripMetadata]
    error: Optional[str]
    is_valid: bool
    validation_errors: List[str]
    trip_duration: Optional[int]

async def trip_validator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate trip parameters from the metadata.
    
    Args:
        state: Current state containing trip metadata
        
    Returns:
        Updated state with validation status
    """
    # Extract metadata
    metadata: Optional[TripMetadata] = state.get("metadata")
    
    if not metadata:
        state["error"] = "No trip metadata available for validation"
        state["is_valid"] = False
        return state
    
    # Initialize validation
    errors = []
    
    # Validate source and destination
    if not metadata.source:
        errors.append("Source location is required")
    
    if not metadata.destination:
        errors.append("Destination location is required")
    
    if metadata.source and metadata.destination and metadata.source.lower() == metadata.destination.lower():
        errors.append("Source and destination cannot be the same")
    
    # Validate dates
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if not metadata.start_date:
        errors.append("Start date is required")
    elif metadata.start_date < today:
        errors.append("Start date must be in the future")
    
    if not metadata.end_date:
        errors.append("End date is required")
    elif metadata.end_date < today:
        errors.append("End date must be in the future")
    
    # Validate date order and duration
    if metadata.start_date and metadata.end_date:
        if metadata.end_date < metadata.start_date:
            errors.append("End date cannot be before start date")
        
        duration = (metadata.end_date - metadata.start_date).days
        if duration > 14:
            errors.append("Trip duration cannot exceed 14 days")
        
        # Add duration to state
        state["trip_duration"] = duration
    
    # Validate number of people
    if metadata.num_people < 1:
        errors.append("Number of people must be at least 1")
    
    # Update state with validation results
    state["validation_errors"] = errors
    state["is_valid"] = len(errors) == 0
    
    return state 