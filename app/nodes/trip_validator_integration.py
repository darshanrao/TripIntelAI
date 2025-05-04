import asyncio
from typing import Dict, Any, Optional
from app.nodes.interactive_trip_validator_node import (
    interactive_trip_validator_node,
    process_user_response
)

async def integrated_trip_validator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    An integration wrapper for the interactive trip validator that can be inserted
    into the LangGraph pipeline. This node handles the interaction flow between
    the pipeline and the validator.
    
    Args:
        state: The current state object containing query and metadata
        
    Returns:
        Updated state with is_valid flag and complete metadata
    """
    # First run through the validator to check for missing fields
    state = await interactive_trip_validator_node(state)
    
    # If all fields are present, return the validated state
    if state.get("is_valid", False):
        return state
    
    # If we're in interactive mode, handle the chat interaction
    if state.get("interactive_mode") and state.get("next_question"):
        return state
    
    # If something went wrong and we don't have is_valid or interactive_mode,
    # just return the state as is
    return state

async def process_interactive_response(state: Dict[str, Any], user_response: str) -> Dict[str, Any]:
    """
    Process a user's response in interactive mode and update the state
    
    Args:
        state: Current state with missing_fields and metadata
        user_response: The user's text response to the question
        
    Returns:
        Updated state with the user's response integrated
    """
    # Process the response
    state = await process_user_response(state, user_response)
    
    # If all fields are now present, return the validated state
    if state.get("is_valid", False):
        return state
    
    # If we're still in interactive mode with more fields to fill,
    # the state will contain the next_question
    return state

# Example usage in a pipeline
async def example_pipeline_integration():
    """Example of how to integrate the interactive validator into a pipeline"""
    # Initial state with a query
    state = {
        "query": "I want to plan a trip to Hawaii",
        "metadata": type('obj', (object,), {
            "source": None,
            "destination": "Hawaii",  # Already extracted from initial query
            "start_date": None,
            "end_date": None,
            "num_people": None,
            "preferences": None
        })
    }
    
    # Initialize conversation
    print("User: I want to plan a trip to Hawaii")
    
    # Step 1: Run the validator node
    state = await integrated_trip_validator_node(state)
    
    # While we're in interactive mode and have more questions
    while state.get("interactive_mode") and state.get("next_question"):
        # Display the next question to the user
        print(f"Assistant: {state['next_question']}")
        
        # Get the user's response (in a real application, this would come from the UI)
        user_input = input("User: ")
        
        # Process the response
        state = await process_interactive_response(state, user_input)
    
    # Once all required information is gathered, proceed with the rest of the pipeline
    if state.get("is_valid", False):
        print("\nAssistant: Great! I have all the information I need for your trip to Hawaii.")
        print("Trip details:")
        print(f"- From: {state['metadata'].source}")
        print(f"- To: {state['metadata'].destination}")
        print(f"- Start date: {state['metadata'].start_date}")
        print(f"- End date: {state['metadata'].end_date}")
        print(f"- Number of people: {state['metadata'].num_people}")
        
        print("\nNow I'll generate your itinerary...")
        
        # Here we would continue with the rest of the pipeline:
        # state = await planner_node(state)
        # and call subsequent nodes based on nodes_to_call list
        
        # For demo, we'll just show a simple itinerary response
        print("\nAssistant: Here's your personalized Hawaii itinerary:")
        print("-" * 50)
        print(f"Day 1: Arrival in Hawaii")
        print(f"Day 2: Beach day and luau")
        print(f"Day 3: Volcano National Park")
        print(f"Day 4: Snorkeling adventure")
        print(f"Day 5: Departure")
        print("-" * 50)
    else:
        print("\nAssistant: I'm sorry, but I couldn't create an itinerary with the information provided.")
        print(f"Issues: {', '.join(state.get('validation_errors', ['Unknown error']))}")

# Example of how to integrate with FastAPI
"""
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # Initialize or retrieve the conversation state
    if request.conversation_id and request.conversation_id in conversation_states:
        state = conversation_states[request.conversation_id]
    else:
        # New conversation
        request.conversation_id = str(uuid.uuid4())
        state = {"query": request.query}
        
        # Process through initial nodes
        state = await chat_input_node(state)
        state = await intent_parser_node(state)
        
    # Check if we're in the middle of an interactive validation
    if state.get("interactive_mode") and request.query:
        # Process the user's response to the previous question
        state = await process_interactive_response(state, request.query)
    elif not state.get("is_valid", False):
        # Run the validator if we haven't validated yet
        state = await integrated_trip_validator_node(state)
    
    # If validation is complete, continue with the pipeline
    if state.get("is_valid", True) and not state.get("interactive_mode", False):
        # Continue with the rest of the pipeline
        state = await planner_node(state)
        # ... other nodes
        state = await summary_node(state)
        
        # Return the completed itinerary
        return ChatResponse(
            itinerary=state.get("itinerary"),
            is_valid=True,
            conversation_id=request.conversation_id
        )
    
    # If we're still in interactive mode, return the next question
    if state.get("interactive_mode") and state.get("next_question"):
        # Save the current state for the next request
        conversation_states[request.conversation_id] = state
        
        # Return the next question without an itinerary
        return ChatResponse(
            itinerary=None,
            is_valid=None,
            conversation_id=request.conversation_id,
            next_question=state["next_question"]
        )
    
    # Handle validation errors
    return ChatResponse(
        itinerary=None,
        is_valid=False,
        validation_errors=state.get("validation_errors", ["Unknown validation error"]),
        conversation_id=request.conversation_id
    )
"""

if __name__ == "__main__":
    # Run the example to demonstrate interactive validation
    asyncio.run(example_pipeline_integration()) 