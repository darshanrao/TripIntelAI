import asyncio
import os
import time
import threading
from dotenv import load_dotenv

# Import the individual components
from app.nodes.chat_input_node import chat_input_node
from mock_intent_parser import mock_intent_parser  # Use mock parser
from app.nodes.trip_validator_node import trip_validator_node
from app.nodes.planner_node import planner_node
from app.nodes.agent_nodes import flights_node, places_node, restaurants_node, hotel_node, budget_node, reviews_node
from app.nodes.summary_node import summary_node

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

async def process_travel_query(query, spinner):
    """Process a travel query using the individual components"""
    # Initial state
    state = {"query": query}
    
    # Step 1: Chat Input Node
    spinner.message = "Parsing your travel query"
    state = await chat_input_node(state)
    
    # Step 2: Intent Parser Node (using mock)
    spinner.message = "Extracting travel details"
    state = await mock_intent_parser(state)
    
    # Step 3: Trip Validator Node
    spinner.message = "Validating your travel plans"
    state = await trip_validator_node(state)
    
    # Check if trip is valid
    if not state.get('is_valid', False):
        return state
    
    # Step 4: Planner Node
    spinner.message = "Planning your trip components"
    state = await planner_node(state)
    
    # Step 5: Agent Nodes
    nodes_to_call = state.get('nodes_to_call', [])
    
    if 'flights' in nodes_to_call:
        spinner.message = "Searching for flights"
        state = await flights_node(state)
    
    if 'places' in nodes_to_call:
        spinner.message = "Finding interesting places to visit"
        state = await places_node(state)
    
    if 'restaurants' in nodes_to_call:
        spinner.message = "Discovering local restaurants"
        state = await restaurants_node(state)
    
    if 'hotel' in nodes_to_call:
        spinner.message = "Locating suitable accommodations"
        state = await hotel_node(state)
    
    if 'budget' in nodes_to_call:
        spinner.message = "Calculating trip budget"
        state = await budget_node(state)
    
    # Step 6: Reviews Node
    spinner.message = "Analyzing reviews for better recommendations"
    state = await reviews_node(state)
    
    # Step 7: Summary Node
    spinner.message = "Generating your personalized itinerary"
    state = await summary_node(state)
    
    return state

def display_random_travel_facts(spinner):
    """Display random travel facts while loading"""
    travel_facts = [
        "The world's shortest commercial flight is between Westray and Papa Westray in Scotland's Orkney Islands, lasting just under 2 minutes.",
        "France is the most visited country in the world, with over 89 million annual tourists.",
        "The Great Wall of China is not visible from space with the naked eye, contrary to popular belief.",
        "There are 195 recognized countries in the world today.",
        "Japan has more than 1,500 earthquakes every year.",
        "The passport color of most countries is either red, blue, green, or black.",
        "San Marino is the world's oldest republic, founded in 301 CE.",
        "The International Date Line isn't straight - it zigzags to avoid splitting countries into different days.",
        "Vatican City is the smallest country in the world, with an area of just 0.17 square miles.",
        "The word 'travel' comes from the French word 'travail', which means 'work'.",
        "The average airplane meal loses 30% of its taste at high altitude due to cabin pressure.",
        "Australia is the only continent without an active volcano.",
        "Singapore's Changi Airport has a butterfly garden with over 1,000 butterflies.",
        "The Dead Sea is so salty that people can easily float on top of it.",
        "More than half of the world's population has never made or received a telephone call."
    ]
    
    import random
    random.shuffle(travel_facts)
    
    for fact in travel_facts:
        spinner.message = f"Did you know? {fact}"
        time.sleep(4)  # Show each fact for 4 seconds

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
        
        # Start facts thread
        facts_thread = threading.Thread(target=display_random_travel_facts, args=(spinner,))
        facts_thread.daemon = True
        facts_thread.start()
        
        try:
            # Process the query
            result = await process_travel_query(query, spinner)
            
            # Stop spinner
            spinner.stop()
            
            # Check if validation passed
            if not result.get("is_valid", False):
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