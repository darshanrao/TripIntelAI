from datetime import datetime, timedelta

# Create mock trip data
def create_mock_trip_data():
    """
    Create mock trip data for testing the itinerary planner.
    """
    start_date = datetime.now() + timedelta(days=30)  # Start date is 30 days from now
    
    return {
        "destination": "Paris",
        "start_date": start_date.strftime("%Y-%m-%d"),
        "total_days": 3,
        "flights": [
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
        ],
        "hotel": {
            "name": "Hotel de Luxe Paris",
            "location": "15 Rue de Rivoli, 75004 Paris, France",
            "price_per_night": 250.00,
            "rating": 4.7,
            "amenities": ["WiFi", "Breakfast", "Air Conditioning"]
        },
        "places": [
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
        ],
        "restaurants": [
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
        ],
        "budget": {
            "total": 2000,
            "accommodation": 750,
            "food": 500,
            "activities": 500,
            "transportation": 250
        }
    }

if __name__ == "__main__":
    import json
    # Print the mock data in JSON format
    print(json.dumps(create_mock_trip_data(), indent=2)) 