import asyncio
import json
import sys
import os
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the classes needed for testing
from app.nodes.interactive_trip_validator_node import (
    interactive_trip_validator_node,
    process_user_response
)

# Load environment variables
load_dotenv()

class TripMetadata:
    """Simple class to hold trip metadata."""
    def __init__(self):
        self.source = None
        self.destination = None
        self.start_date = None
        self.end_date = None
        self.num_people = None
        self.preferences = None

async def test_enhanced_validator():
    """
    Test the enhanced interactive validator with Claude integration.
    This demonstrates how the validator can understand natural language responses.
    """
    print("\n" + "=" * 80)
    print("🌍 TripIntelAI Enhanced Validator Test with ReAct Framework 🌍")
    print("=" * 80)
    print("This test showcases the improved validator with natural language understanding.")
    print("You can now enter dates, locations, and numbers in conversational language.")
    print("-" * 80)
    print("Examples of what you can now say:")
    print("• When asked for a date: 'sometime in July', 'next Monday', 'around Christmas'")
    print("• When asked for people: 'just me and my wife', 'a family of four', 'a small group'")
    print("• When asked for locations: 'somewhere in the Bahamas', 'the Big Apple', 'wine country'")
    print("• For any field, you can say: 'anything is fine', 'you decide', 'whatever works best'")
    print("-" * 80)
    
    # Get the initial query
    query = input("\nEnter your travel query (e.g., 'I want to visit Miami next month'): ")
    
    # Create initial state with the query
    state = {
        "query": query,
        "metadata": TripMetadata()
    }
    
    # Process through the validator
    state = await interactive_trip_validator_node(state)
    
    # Interactive chat loop
    while state.get("interactive_mode") and state.get("next_question"):
        # Display the question to the user
        print(f"\nAssistant: {state['next_question']}")
        
        # Get the user's response
        user_input = input("You: ")
        
        print("Processing your response with Claude AI...")
        state = await process_user_response(state, user_input)
        
        # Display acknowledgments if any
        if state.get("conversation_history"):
            # Find the last assistant message that isn't the next question
            next_question = state.get("next_question", "")
            for message in reversed(state["conversation_history"]):
                if message["role"] == "assistant" and message["content"] != next_question:
                    # If it's a decision made by the assistant (due to flexibility)
                    if "since you're flexible" in message["content"].lower() or "i've selected" in message["content"].lower():
                        print(f"\nAssistant: {message['content']}")
                    break
    
    # Display the final result
    if state.get("is_valid", False):
        print("\n" + "=" * 80)
        print("✅ All required information has been collected!")
        print("=" * 80)
        print("Trip details:")
        print(f"- From: {state['metadata'].source}")
        print(f"- To: {state['metadata'].destination}")
        print(f"- Start date: {state['metadata'].start_date}")
        print(f"- End date: {state['metadata'].end_date}")
        print(f"- Number of people: {state['metadata'].num_people}")
        if hasattr(state['metadata'], 'preferences') and state['metadata'].preferences:
            print(f"- Preferences: {', '.join(state['metadata'].preferences) if isinstance(state['metadata'].preferences, list) else state['metadata'].preferences}")
        
        print("\nIn a real application, this would now continue to the next steps of the pipeline:")
        print("1. Planning which components to use")
        print("2. Gathering information about flights, accommodations, etc.")
        print("3. Generating a detailed itinerary")
        
        # Show conversation history for review
        if "--conversation" in sys.argv:
            print("\nFull conversation:")
            for message in state.get("conversation_history", []):
                role = "You" if message["role"] == "user" else "Assistant"
                print(f"{role}: {message['content']}")
        
        # Show state for debugging
        if "--debug" in sys.argv:
            print("\nDebug - Final state:")
            print(json.dumps({k: str(v) for k, v in state.items() if k != "conversation_history"}, indent=2))
    else:
        print("\n" + "=" * 80)
        print("❌ Validation failed!")
        print("=" * 80)
        print("Errors:")
        for error in state.get("validation_errors", ["Unknown error"]):
            print(f"- {error}")

async def test_flexible_responses():
    """
    Test the assistant's ability to handle flexible responses like 
    "anything is fine" or "you decide".
    """
    print("\n" + "=" * 80)
    print("🔄 Flexible Response Testing 🔄")
    print("=" * 80)
    print("This test shows how the assistant can make decisions when you're flexible.")
    print("Try responding with phrases like 'anything works', 'you decide', 'I'm flexible'")
    print("-" * 80)
    
    # Create initial state with minimal query
    state = {
        "query": "I want to plan a trip",
        "metadata": TripMetadata()
    }
    
    # Process through the validator to get the first question
    state = await interactive_trip_validator_node(state)
    
    print(f"\nAssistant: {state['next_question']}")
    print("You: New York")  # Set a fixed destination
    
    # Process the response
    state = await process_user_response(state, "New York")
    
    # Show the next question and ask for a flexible response
    print(f"\nAssistant: {state['next_question']}")
    print("You: anything is fine")
    
    # Process the flexible response
    state = await process_user_response(state, "anything is fine")
    
    # Display the decision made by the assistant
    for message in reversed(state["conversation_history"]):
        if message["role"] == "assistant" and "since you're flexible" in message["content"].lower():
            print(f"\nAssistant: {message['content']}")
            break
    
    # Continue with another flexible response
    if state.get("next_question"):
        print(f"\nAssistant: {state['next_question']}")
        print("You: you decide what's best")
        
        # Process another flexible response
        state = await process_user_response(state, "you decide what's best")
        
        # Display the decision
        for message in reversed(state["conversation_history"]):
            if message["role"] == "assistant" and "i've selected" in message["content"].lower():
                print(f"\nAssistant: {message['content']}")
                break
    
    # Show the final collected information
    print("\nInformation decided by AI when user was flexible:")
    for field in ["source", "destination", "start_date", "end_date", "num_people"]:
        if hasattr(state["metadata"], field) and getattr(state["metadata"], field):
            print(f"- {field}: {getattr(state['metadata'], field)}")

async def compare_extractors():
    """Demonstrate the difference between basic and enhanced extraction"""
    from app.nodes.enhanced_extractor import enhanced_date_extraction, enhanced_number_extraction
    
    print("\n" + "=" * 80)
    print("🔄 Comparing Basic vs Enhanced Extraction 🔄")
    print("=" * 80)
    
    # Test cases for dates
    date_tests = [
        "may 16",
        "next friday",
        "sometime in july",
        "around christmas",
        "three weeks from now",
        "early next month",
        "the weekend after labor day"
    ]
    
    print("\nDATE EXTRACTION:")
    print("-" * 40)
    from app.nodes.interactive_trip_validator_node import _extract_date
    
    for test in date_tests:
        basic = _extract_date(test)
        context = {"destination": "Hawaii"}
        enhanced = await enhanced_date_extraction(test, "start_date", context)
        print(f'Input: "{test}"')
        print(f'  Basic extraction: {basic or "Failed"}')
        print(f'  Enhanced extraction: {enhanced or "Failed"}')
        print()
    
    # Test cases for numbers
    number_tests = [
        "2",
        "just me and my wife",
        "a family of four",
        "my partner and I",
        "two adults and a child",
        "a small group of friends"
    ]
    
    print("\nNUMBER EXTRACTION:")
    print("-" * 40)
    from app.nodes.interactive_trip_validator_node import _extract_number
    
    for test in number_tests:
        basic = _extract_number(test)
        enhanced = await enhanced_number_extraction(test)
        print(f'Input: "{test}"')
        print(f'  Basic extraction: {basic or "Failed"}')
        print(f'  Enhanced extraction: {enhanced or "Failed"}')
        print()

async def main():
    """Main entry point."""
    print("\nWhat would you like to do?")
    print("1. Test the enhanced conversational validator")
    print("2. Test handling of flexible responses")
    print("3. Compare basic vs enhanced extraction capabilities")
    choice = input("Enter your choice (1, 2, or 3): ")
    
    if choice == "2":
        await test_flexible_responses()
    elif choice == "3":
        await compare_extractors()
    else:
        await test_enhanced_validator()
    
    # Ask if user wants to run another test
    while True:
        again = input("\nWould you like to run another test? (y/n): ")
        if again.lower() not in ['y', 'yes']:
            print("\nThank you for testing the enhanced validator! Goodbye!")
            break
            
        print("\nWhat would you like to do?")
        print("1. Test the enhanced conversational validator")
        print("2. Test handling of flexible responses")
        print("3. Compare basic vs enhanced extraction capabilities")
        choice = input("Enter your choice (1, 2, or 3): ")
        
        if choice == "2":
            await test_flexible_responses()
        elif choice == "3":
            await compare_extractors()
        else:
            await test_enhanced_validator()

if __name__ == "__main__":
    # Run the test
    asyncio.run(main()) 