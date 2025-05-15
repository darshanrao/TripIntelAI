import asyncio
import os
from datetime import datetime, timedelta
from app.nodes.agents.itinerary_planner_node import itinerary_planner_node, GraphState

async def test_itinerary_planner():
    # Test Case 1: First day of trip
    state_day1: GraphState = {
        "current_day": 1,
        "total_days": 3,
        "destination": "Paris",
        "start_date": "2024-05-15",
        "flights": [
            {
                "type": "arrival",
                "airline": "Air France",
                "flight_number": "AF123",
                "arrival_time": "10:00",
                "airport": "CDG"
            }
        ],
        "places": [
            {
                "name": "Eiffel Tower",
                "type": "attraction",
                "category": "landmark",
                "rating": 4.7,
                "price": 25
            },
            {
                "name": "Louvre Museum",
                "type": "attraction",
                "category": "museum",
                "rating": 4.8,
                "price": 17
            }
        ],
        "restaurants": [
            {
                "name": "Le Jules Verne",
                "type": "dining",
                "category": "fine_dining",
                "rating": 4.6,
                "price": 200
            },
            {
                "name": "Café de Flore",
                "type": "dining",
                "category": "cafe",
                "rating": 4.4,
                "price": 50
            }
        ],
        "hotel": {
            "name": "Hotel Ritz Paris",
            "type": "accommodation",
            "category": "luxury",
            "rating": 4.9,
            "price": 1000,
            "check_in": "15:00",
            "check_out": "12:00"
        },
        "budget": {
            "total": 5000,
            "daily": 1500,
            "currency": "EUR"
        },
        "route": {},
        "daily_itineraries": [],
        "visited_places": set(),
        "visited_restaurants": set(),
        "final_itinerary": None
    }

    # Test Case 2: Middle day of trip
    state_day2: GraphState = {
        "current_day": 2,
        "total_days": 3,
        "destination": "Paris",
        "start_date": "2024-05-15",
        "flights": [],
        "places": [
            {
                "name": "Notre-Dame Cathedral",
                "type": "attraction",
                "category": "church",
                "rating": 4.7,
                "price": 0
            },
            {
                "name": "Musée d'Orsay",
                "type": "attraction",
                "category": "museum",
                "rating": 4.8,
                "price": 16
            }
        ],
        "restaurants": [
            {
                "name": "L'Ami Louis",
                "type": "dining",
                "category": "bistro",
                "rating": 4.5,
                "price": 100
            }
        ],
        "hotel": {
            "name": "Hotel Ritz Paris",
            "type": "accommodation",
            "category": "luxury",
            "rating": 4.9,
            "price": 1000,
            "check_in": "15:00",
            "check_out": "12:00"
        },
        "budget": {
            "total": 5000,
            "daily": 1500,
            "currency": "EUR"
        },
        "route": {},
        "daily_itineraries": [
            {
                "date": "2024-05-15",
                "activities": [
                    {
                        "type": "transportation",
                        "category": "flight",
                        "title": "Air France AF123",
                        "time": "10:00",
                        "duration_minutes": 120,
                        "details": {},
                        "review_insights": {}
                    },
                    {
                        "type": "accommodation",
                        "category": "hotel",
                        "title": "Hotel Ritz Paris",
                        "time": "15:00",
                        "duration_minutes": 30,
                        "details": {},
                        "review_insights": {}
                    }
                ]
            }
        ],
        "visited_places": {"Eiffel Tower", "Louvre Museum"},
        "visited_restaurants": {"Le Jules Verne"},
        "final_itinerary": None
    }

    # Test Case 3: Last day of trip
    state_day3: GraphState = {
        "current_day": 3,
        "total_days": 3,
        "destination": "Paris",
        "start_date": "2024-05-15",
        "flights": [
            {
                "type": "departure",
                "airline": "Air France",
                "flight_number": "AF124",
                "departure_time": "18:00",
                "airport": "CDG"
            }
        ],
        "places": [],
        "restaurants": [],
        "hotel": {
            "name": "Hotel Ritz Paris",
            "type": "accommodation",
            "category": "luxury",
            "rating": 4.9,
            "price": 1000,
            "check_in": "15:00",
            "check_out": "12:00"
        },
        "budget": {
            "total": 5000,
            "daily": 1500,
            "currency": "EUR"
        },
        "route": {},
        "daily_itineraries": [
            {
                "date": "2024-05-15",
                "activities": [
                    {
                        "type": "transportation",
                        "category": "flight",
                        "title": "Air France AF123",
                        "time": "10:00",
                        "duration_minutes": 120,
                        "details": {},
                        "review_insights": {}
                    },
                    {
                        "type": "accommodation",
                        "category": "hotel",
                        "title": "Hotel Ritz Paris",
                        "time": "15:00",
                        "duration_minutes": 30,
                        "details": {},
                        "review_insights": {}
                    }
                ]
            },
            {
                "date": "2024-05-16",
                "activities": [
                    {
                        "type": "attraction",
                        "category": "church",
                        "title": "Notre-Dame Cathedral",
                        "time": "10:00",
                        "duration_minutes": 120,
                        "details": {},
                        "review_insights": {}
                    }
                ]
            }
        ],
        "visited_places": {"Eiffel Tower", "Louvre Museum", "Notre-Dame Cathedral", "Musée d'Orsay"},
        "visited_restaurants": {"Le Jules Verne", "L'Ami Louis", "Café de Flore"},
        "final_itinerary": None
    }

    # Run tests
    test_cases = [
        ("Day 1", state_day1),
        ("Day 2", state_day2),
        ("Day 3", state_day3)
    ]

    for test_name, state in test_cases:
        print(f"\nTesting {test_name}...")
        result = await itinerary_planner_node(state)
        
        # Verify the result
        assert "error" not in result or not result["error"], f"Error in {test_name}: {result.get('error')}"
        assert "daily_itineraries" in result, f"Missing daily_itineraries in {test_name}"
        assert len(result["daily_itineraries"]) > 0, f"No itineraries generated for {test_name}"
        
        # Verify the latest itinerary
        latest_itinerary = result["daily_itineraries"][-1]
        assert "date" in latest_itinerary, f"Missing date in {test_name} itinerary"
        assert "activities" in latest_itinerary, f"Missing activities in {test_name} itinerary"
        
        # Verify activities
        for activity in latest_itinerary["activities"]:
            assert "type" in activity, f"Missing type in activity for {test_name}"
            assert "category" in activity, f"Missing category in activity for {test_name}"
            assert "title" in activity, f"Missing title in activity for {test_name}"
            assert "time" in activity, f"Missing time in activity for {test_name}"
            assert "duration_minutes" in activity, f"Missing duration_minutes in activity for {test_name}"
        
        print(f"{test_name} test passed!")
        print(f"Generated {len(latest_itinerary['activities'])} activities")
        print("Activities:", [f"{a['time']} - {a['title']}" for a in latest_itinerary['activities']])

if __name__ == "__main__":
    asyncio.run(test_itinerary_planner()) 