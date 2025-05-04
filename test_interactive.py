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

async def test_interactive_validator():
    """
    Test the interactive validator in a command-line chat interface.
    This simulates how the validator would work in a real chat application.
    """
    print("\n" + "=" * 80)
    print("🌍 TripIntelAI Interactive Validator Test 🌍")
    print("=" * 80)
    print("This test allows you to test the interactive trip validator.")
    print("Enter your initial query to start planning a trip.")
    print("-" * 80)
    
    # Get the initial query
    query = input("\nEnter your travel query: ")
    
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
        
        # Process the response
        state = await process_user_response(state, user_input)
    
    # Display the final result
    if state.get("is_valid", False):
        print("\n" + "=" * 80)
        print("✅ All required information has been collected!")
        print("=" * 80)
        print("Trip details:")
        print(f"- Source: {state['metadata'].source}")
        print(f"- Destination: {state['metadata'].destination}")
        print(f"- Start date: {state['metadata'].start_date}")
        print(f"- End date: {state['metadata'].end_date}")
        print(f"- Number of people: {state['metadata'].num_people}")
        if hasattr(state['metadata'], 'preferences') and state['metadata'].preferences:
            print(f"- Preferences: {', '.join(state['metadata'].preferences)}")
        
        print("\nIn a real application, this would now continue to the next steps of the pipeline:")
        print("1. Planning which components to use")
        print("2. Gathering information about flights, accommodations, etc.")
        print("3. Generating a detailed itinerary")
        
        # Show state for debugging
        if "--debug" in sys.argv:
            print("\nDebug - Final state:")
            print(json.dumps({k: str(v) for k, v in state.items()}, indent=2))
    else:
        print("\n" + "=" * 80)
        print("❌ Validation failed!")
        print("=" * 80)
        print("Errors:")
        for error in state.get("validation_errors", ["Unknown error"]):
            print(f"- {error}")

async def main():
    """Main entry point."""
    await test_interactive_validator()
    
    # Ask if user wants to run another test
    while True:
        again = input("\nWould you like to run another test? (y/n): ")
        if again.lower() not in ['y', 'yes']:
            print("\nThank you for testing the interactive validator! Goodbye!")
            break
        await test_interactive_validator()

if __name__ == "__main__":
    # Run the test
    asyncio.run(main()) 