import asyncio
import os
import time
import threading
from dotenv import load_dotenv
from app.graph.trip_planner_graph_mock import TripPlannerGraphMock

# Load environment variables
load_dotenv()

class Spinner:
    """Simple spinner animation for loading status"""
    def __init__(self, message="Processing"):
        self.message = message
        self.spinning = False
        self.spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.spinner_thread = None

    def spin(self):
        i = 0
        while self.spinning:
            i = (i + 1) % len(self.spinner_chars)
            print(f"\r{self.spinner_chars[i]} {self.message}...", end="", flush=True)
            time.sleep(0.1)

    def start(self):
        self.spinning = True
        self.spinner_thread = threading.Thread(target=self.spin)
        self.spinner_thread.daemon = True
        self.spinner_thread.start()

    def stop(self):
        self.spinning = False
        if self.spinner_thread:
            self.spinner_thread.join()
        print("\r", end="", flush=True)

async def process_travel_query(query):
    """Process a travel query using the trip planner pipeline"""
    # Initialize the trip planner graph
    trip_planner = TripPlannerGraphMock()
    
    # Process the query
    result = await trip_planner.process(query)
    return result

def display_loading_messages(spinner):
    """Update spinner with various loading messages"""
    loading_messages = [
        "Analyzing your travel preferences",
        "Checking flight availability",
        "Finding the best places to visit",
        "Discovering local cuisine options",
        "Locating suitable accommodations",
        "Optimizing your itinerary",
        "Finalizing travel plans",
        "Preparing your personalized itinerary"
    ]
    
    for message in loading_messages:
        spinner.message = message
        time.sleep(2)  # Show each message for 2 seconds

async def main():
    print("=" * 80)
    print("🌍 Welcome to TripIntelAI - Your AI Travel Planner 🌍")
    print("=" * 80)
    print("Please enter your travel query. For example:")
    print("  'I want to plan a trip from Boston to NYC from May 15 to May 18, 2025 for 2 people'")
    print("  'Plan a family vacation to Paris in summer for 5 days with focus on museums'")
    print("-" * 80)
    
    while True:
        # Get user input
        query = input("\nEnter your travel query (or 'exit' to quit): ")
        
        if query.lower() in ['exit', 'quit', 'q']:
            print("\nThank you for using TripIntelAI. Have a great trip! 👋")
            break
        
        if not query.strip():
            print("Please enter a valid query.")
            continue
        
        # Start loading spinner
        spinner = Spinner("Processing your travel request")
        spinner.start()
        
        # Start message thread
        message_thread = threading.Thread(target=display_loading_messages, args=(spinner,))
        message_thread.daemon = True
        message_thread.start()
        
        try:
            # Process the query
            result = await process_travel_query(query)
            
            # Stop spinner
            spinner.stop()
            
            # Check if validation passed
            if not result.get("is_valid", True):
                print("\n❌ Your travel query couldn't be processed:")
                for error in result.get("validation_errors", []):
                    print(f"  - {error}")
                print("\nPlease try again with more specific information.")
                continue
            
            # Print the generated itinerary
            print("\n✨ Your personalized travel itinerary is ready! ✨\n")
            print("-" * 80)
            print(result.get("itinerary", "No itinerary could be generated."))
            print("-" * 80)
            
        except Exception as e:
            # Stop spinner
            spinner.stop()
            print(f"\n❌ An error occurred: {str(e)}")
            print("Please try again with a different query.")
        
        # Ask if user wants to plan another trip
        another = input("\nWould you like to plan another trip? (y/n): ")
        if another.lower() not in ['y', 'yes']:
            print("\nThank you for using TripIntelAI. Have a great trip! 👋")
            break

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main()) 