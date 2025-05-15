import asyncio
import json
import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from app.utils.logger import logger
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Define our own prompt template
DAILY_PLANNER_PROMPT = """You are a daily itinerary planner. Create a detailed schedule for day {current_day} of a {total_days}-day trip to Paris.

Trip Information:
- Day of trip: {current_day} of {total_days}
- Destination: Paris
- Travelers: 2 people
- Preferences: museums, historical sites, local cuisine
- Date: {date}

Available information:
- Flights: {flights}
- Hotel: {hotel}
- Budget per person: {budget}

Available places to visit (not yet visited):
{places}

Available restaurants (not yet visited):
{restaurants}

Already visited places:
{visited_places}

Already visited restaurants:
{visited_restaurants}

Create a schedule that:
1. For day 1: Start with flight arrival and hotel check-in
2. For day {total_days}: End with flight departure and hotel check-out
3. For other days: Include breakfast, lunch, and dinner
4. Includes nearby attractions grouped together
5. Includes meals at appropriate times
6. Stays within budget
7. Avoids revisiting places already visited

Return the schedule as a JSON object in EXACTLY this format:
{{
  "date": "{date}",
  "activities": [
    {{
      "type": "accommodation|dining|attraction|transportation",
      "category": "hotel|breakfast|lunch|dinner|museum|park|theme park|flight|etc",
      "title": "Name of the activity",
      "time": "HH:MM",
      "duration_minutes": duration_in_minutes,
      "details": {{}},
      "review_insights": {{
        "sentiment": "positive|neutral|negative",
        "strengths": [],
        "weaknesses": [],
        "summary": "Brief summary"
      }}
    }}
  ]
}}

Leave the "details" and "review_insights" fields as empty objects/arrays, but include them in the structure.
Make sure to include appropriate activities for the time of day (morning, afternoon, evening).
"""

async def test_itinerary_planner():
    """
    Test the itinerary planner with a simplified approach.
    """
    print("\n=== Testing Itinerary Planner ===")
    
    # Create mock data
    start_date = datetime.now() + timedelta(days=30)  # Start date is 30 days from now
    
    flights = [
        {
            "id": "F123",
            "airline": "Air France",
            "flight_number": "AF1234",
            "departure_airport": "SFO",
            "departure_city": "San Francisco",
            "arrival_airport": "CDG",
            "arrival_city": "Paris",
            "departure_time": start_date.strftime("%Y-%m-%dT08:00:00"),
            "arrival_time": start_date.strftime("%Y-%m-%dT16:30:00"),
            "price": 850.00
        },
        {
            "id": "F456",
            "airline": "Air France",
            "flight_number": "AF1235",
            "departure_airport": "CDG",
            "departure_city": "Paris",
            "arrival_airport": "SFO",
            "arrival_city": "San Francisco",
            "departure_time": (start_date + timedelta(days=2)).strftime("%Y-%m-%dT18:00:00"),
            "arrival_time": (start_date + timedelta(days=2)).strftime("%Y-%m-%dT21:30:00"),
            "price": 870.00
        }
    ]
    
    hotel = {
        "name": "Hotel de Luxe Paris",
        "location": "15 Rue de Rivoli, 75004 Paris, France",
        "price_per_night": 250.00,
        "rating": 4.7,
        "amenities": ["WiFi", "Breakfast", "Air Conditioning"]
    }
    
    attractions = [
        {
            "name": "Eiffel Tower",
            "location": "Champ de Mars, 5 Avenue Anatole France, 75007 Paris",
            "rating": 4.6,
            "type": "tourist_attraction"
        },
        {
            "name": "Louvre Museum",
            "location": "Rue de Rivoli, 75001 Paris",
            "rating": 4.7,
            "type": "museum"
        },
        {
            "name": "Notre-Dame Cathedral",
            "location": "6 Parvis Notre-Dame - Pl. Jean-Paul II, 75004 Paris",
            "rating": 4.7,
            "type": "tourist_attraction"
        },
        {
            "name": "Arc de Triomphe",
            "location": "Place Charles de Gaulle, 75008 Paris",
            "rating": 4.7,
            "type": "monument"
        },
        {
            "name": "Musée d'Orsay",
            "location": "1 Rue de la Légion d'Honneur, 75007 Paris",
            "rating": 4.7,
            "type": "museum"
        },
        {
            "name": "Sacré-Cœur",
            "location": "35 Rue du Chevalier de la Barre, 75018 Paris",
            "rating": 4.8,
            "type": "religious_site"
        }
    ]
    
    restaurants = [
        {
            "name": "Le Jules Verne",
            "location": "Eiffel Tower, Avenue Gustave Eiffel, 75007 Paris",
            "rating": 4.5,
            "cuisine": "French",
            "price_range": "$$$"
        },
        {
            "name": "Café de Flore",
            "location": "172 Boulevard Saint-Germain, 75006 Paris",
            "rating": 4.2,
            "cuisine": "French",
            "price_range": "$$$"
        },
        {
            "name": "Le Comptoir du Relais",
            "location": "9 Carrefour de l'Odéon, 75006 Paris",
            "rating": 4.3,
            "cuisine": "French",
            "price_range": "$$$"
        },
        {
            "name": "L'As du Fallafel",
            "location": "34 Rue des Rosiers, 75004 Paris",
            "rating": 4.4,
            "cuisine": "Middle Eastern",
            "price_range": "$"
        },
        {
            "name": "Chez Aline",
            "location": "85 Rue de la Roquette, 75011 Paris",
            "rating": 4.3,
            "cuisine": "French",
            "price_range": "$$"
        }
    ]
    
    budget = 2000
    
    # Initialize variables to track state
    current_day = 1
    total_days = 3
    visited_places = []
    visited_restaurants = []
    
    # Create the final itinerary structure
    final_itinerary = {
        'trip_summary': {
            'destination': 'Paris',
            'start_date': start_date.strftime("%Y-%m-%d"),
            'end_date': (start_date + timedelta(days=total_days-1)).strftime("%Y-%m-%d"),
            'duration_days': total_days,
            'total_budget': budget
        },
        'daily_itinerary': {},
        'review_highlights': {
            'top_rated_places': [],
            'top_rated_restaurants': [],
            'hotel_review_summary': {
                'name': hotel['name'],
                'rating': hotel['rating'],
                'strengths': [],
                'weaknesses': [],
                'summary': ''
            },
            'overall': ["Cultural experience", "Historical sites", "Fine dining"],
            'accommodations': ["Central location", "Comfortable rooms"],
            'dining': ["French cuisine", "Local specialties"],
            'attractions': ["Museums", "Monuments", "Historical sites"]
        }
    }
    
    try:
        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("Error: ANTHROPIC_API_KEY not found in environment variables")
            return None
            
        # Strip any whitespace or newlines
        api_key = api_key.strip()
        
        # Initialize LLM
        llm = ChatAnthropic(
            api_key=api_key,
            model="claude-3-haiku-20240307",
            temperature=0.2,
            max_tokens=1000
        )
        
        # For each day of the trip
        for day in range(1, total_days + 1):
            print(f"\n\n=== Planning Day {day} ===")
            
            # Calculate the date for this day
            current_date = start_date + timedelta(days=day-1)
            date_str = current_date.strftime("%Y-%m-%d")
            
            # Filter out already visited places and restaurants
            available_places = [p for p in attractions if p["name"] not in visited_places]
            available_restaurants = [r for r in restaurants if r["name"] not in visited_restaurants]
            
            # Fill in the prompt
            prompt = DAILY_PLANNER_PROMPT.format(
                current_day=day,
                total_days=total_days,
                date=date_str,
                flights=json.dumps(flights, indent=2),
                hotel=json.dumps(hotel, indent=2),
                budget=budget,
                places=json.dumps(available_places, indent=2),
                restaurants=json.dumps(available_restaurants, indent=2),
                visited_places=json.dumps(visited_places, indent=2),
                visited_restaurants=json.dumps(visited_restaurants, indent=2)
            )
            
            print(f"\nSending prompt to Claude for Day {day}...")
            response = await llm.ainvoke(prompt)
            print(f"\nResponse received from Claude for Day {day}.")
            
            # Parse the response
            content = response.content
            
            # Find the first JSON object in the content
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_content = content[json_start:json_end]
                
                # Parse JSON
                daily_itinerary = json.loads(json_content)
                
                # Update visited places and restaurants from activities
                for activity in daily_itinerary.get('activities', []):
                    if activity.get('type') == 'attraction':
                        visited_places.append(activity.get('title', ''))
                    elif activity.get('type') == 'dining':
                        visited_restaurants.append(activity.get('title', ''))
                
                # Add to final itinerary
                final_itinerary['daily_itinerary'][f'day_{day}'] = daily_itinerary
                
                # Print day itinerary
                print(f"\nDay {day} Itinerary:")
                print("-" * 50)
                print(f"Date: {daily_itinerary.get('date')}")
                for activity in daily_itinerary.get('activities', []):
                    print(f"- {activity.get('time')}: {activity.get('title')}")
                    print(f"  Type: {activity.get('type')}")
                    print(f"  Category: {activity.get('category')}")
                    print(f"  Duration: {activity.get('duration_minutes')} minutes")
                
                # Print places and restaurants visited this day
                print(f"\nPlaces visited on Day {day}:")
                for place in [a.get('title') for a in daily_itinerary.get('activities', []) if a.get('type') == 'attraction']:
                    print(f"- {place}")
                
                print(f"\nRestaurants visited on Day {day}:")
                for restaurant in [a.get('title') for a in daily_itinerary.get('activities', []) if a.get('type') == 'dining']:
                    print(f"- {restaurant}")
            else:
                print(f"Could not find JSON content in the response for Day {day}")
        
        # Print summary of the entire trip
        print("\n\n=== Trip Summary ===")
        print("-" * 50)
        print(f"Destination: {final_itinerary['trip_summary']['destination']}")
        print(f"Start Date: {final_itinerary['trip_summary']['start_date']}")
        print(f"End Date: {final_itinerary['trip_summary']['end_date']}")
        print(f"Total Days: {final_itinerary['trip_summary']['duration_days']}")
        print(f"Budget: ${final_itinerary['trip_summary']['total_budget']}")
        
        print(f"\nAll Places Visited:")
        for place in visited_places:
            print(f"- {place}")
        
        print(f"\nAll Restaurants Visited:")
        for restaurant in visited_restaurants:
            print(f"- {restaurant}")
        
        # Return the final itinerary
        return final_itinerary
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        print(f"\nError occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_itinerary_planner()) 