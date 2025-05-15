from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import time
import os
from datetime import datetime
from dotenv import load_dotenv
from app.graph.trip_planner_graph import TripPlannerGraph
from app.utils.logger import logger
from mock_backend.mock_data import mock_flights  # Temporarily use mock flights
import asyncio

# Load environment variables
load_dotenv()

app = Flask(__name__)
# Configure CORS to allow requests from the frontend
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:3001"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Store conversations
conversations = {}

# Helper functions
def delay(ms):
    time.sleep(ms / 1000)

# Error handler
@app.errorhandler(Exception)
def handle_error(error):
    print(f"Error occurred: {str(error)}")
    return jsonify({
        'success': False,
        'error': str(error),
        'message': 'An error occurred while processing your request'
    }), 500

# Routes
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'message': 'TripIntel backend is running'
    })

@app.route('/conversations', methods=['POST'])
def create_conversation():
    delay(300)
    
    # Generate a new conversation ID
    conversation_id = str(uuid.uuid4())
    
    # Initialize conversation with a welcome message
    conversations[conversation_id] = {
        'messages': [],
        'data': {}
    }
    
    conversations[conversation_id]['messages'].append({
        'id': int(time.time() * 1000),
        'text': "Hi there! I'm your AI travel assistant. Where would you like to go?",
        'sender': 'ai',
        'timestamp': datetime.now().isoformat()
    })
    
    return jsonify({
        'success': True,
        'conversation_id': conversation_id
    })

@app.route('/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    delay(300)
    
    if conversation_id not in conversations:
        return jsonify({
            'success': False,
            'error': 'Conversation not found'
        }), 404
    
    return jsonify({
        'success': True,
        'conversation_id': conversation_id,
        'messages': conversations[conversation_id]['messages']
    })

@app.route('/chat', methods=['POST'])
def chat():
    try:
        delay(1000)
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided',
                'message': 'Please provide request data'
            }), 400
        
        message_type = data.get('type')
        message = data.get('message')
        conversation_id = data.get('conversation_id', str(uuid.uuid4()))
        request_data = data.get('data', {})
        
        print(f"\n=== Received chat request ===")
        print(f"Type: {message_type}")
        print(f"Message: {message}")
        print(f"Conversation ID: {conversation_id}")
        print(f"Data: {request_data}")
        
        # Initialize conversation if it doesn't exist
        if conversation_id not in conversations:
            conversations[conversation_id] = {
                'messages': [],
                'data': {}
            }
        
        if message:
            conversations[conversation_id]['messages'].append({
                'id': int(time.time() * 1000),
                'text': message,
                'sender': 'user',
                'timestamp': datetime.now().isoformat()
            })
        
        if message_type == 'initialize':
            return jsonify({
                'success': True,
                'conversation_id': conversation_id,
                'type': 'initialize',
                'message': "Hi there! I'm your AI travel assistant. Where would you like to go?"
            })
        
        elif message_type == 'info':
            print("\n=== Processing info message ===")
            # Create graph instance
            graph = TripPlannerGraph()
            
            # Initialize state with the user's message
            state = {
                "query": message,
                "raw_query": message,
                "metadata": None,  # Will be populated by the graph
                "is_valid": False,
                "next_question": None,
                "error": None,
                "thought": None,
                "action": None,
                "action_input": None,
                "observation": None,
                "nodes_to_call": [],
                "flights": [],
                "places": [],
                "restaurants": [],
                "hotel": {},
                "budget": {},
                "route": {},
                "current_day": 1,
                "total_days": 1,
                "destination": "",
                "start_date": "",
                "daily_itineraries": [],
                "final_itinerary": None,
                "visited_places": set(),
                "visited_restaurants": set()
            }
            
            print("\n=== Initial State ===")
            print(f"Query: {state['query']}")
            print(f"Raw Query: {state['raw_query']}")
            
            # Process the query
            print("\n=== Processing through graph ===")
            result = asyncio.run(graph.process(state))
            
            print("\n=== Graph Result ===")
            print(f"Is Valid: {result.get('is_valid')}")
            print(f"Next Question: {result.get('next_question')}")
            print(f"Thought: {result.get('thought')}")
            print(f"Action: {result.get('action')}")
            print(f"Error: {result.get('error')}")
            
            # Store the result in conversation data
            conversations[conversation_id]['data']['trip_planner_state'] = result
            
            # Add AI response to conversation
            next_message = result.get('next_question', 'I understand. How else can I help you?')
            conversations[conversation_id]['messages'].append({
                'id': int(time.time() * 1000) + 1,
                'text': next_message,
                'sender': 'ai',
                'timestamp': datetime.now().isoformat()
            })
            
            # Format response based on the state
            response = {
                'success': True,
                'conversation_id': conversation_id,
                'type': 'chat',
                'message': next_message,
                'data': {
                    'is_valid': result.get('is_valid', False),
                    'metadata': result.get('metadata'),
                    'thought': result.get('thought'),
                    'action': result.get('action'),
                    'action_input': result.get('action_input'),
                    'observation': result.get('observation'),
                    'current_day': result.get('current_day', 1),
                    'total_days': result.get('total_days', 1),
                    'destination': result.get('destination', ''),
                    'start_date': result.get('start_date', '')
                }
            }
            
            # If the state is valid and we have flights, add flight data
            if result.get('is_valid', False) and result.get('flights'):
                response['type'] = 'flight_search_outbound'
                response['data']['flights'] = [
                    {**flight, 'id': f'dep-{i}', 'flight_type': 'departure'}
                    for i, flight in enumerate(result['flights'])
                ]
            
            print("\n=== Sending Response ===")
            print(f"Response Type: {response['type']}")
            print(f"Message: {response['message']}")
            print(f"Is Valid: {response['data']['is_valid']}")
            
            return jsonify(response)
        
        elif message_type == 'flight_select_outbound':
            # Process outbound flight selection and search for return flights
            selected_flight_id = request_data.get('selected_flight_id')
            if not selected_flight_id:
                return jsonify({
                    'success': False,
                    'error': 'No flight selected',
                    'message': 'Please select a flight'
                }), 400
            
            # Extract the index from the flight ID (e.g., 'dep-0' -> 0)
            try:
                flight_index = int(selected_flight_id.split('-')[1])
                outbound_flight = mock_flights[flight_index]
            except (IndexError, ValueError):
                # If we can't parse the index, use the first flight
                outbound_flight = mock_flights[0]
            
            # Store the selected outbound flight in the conversation data
            conversations[conversation_id]['data']['selectedOutboundFlight'] = outbound_flight
            
            return jsonify({
                'success': True,
                'conversation_id': conversation_id,
                'type': 'flight_search_inbound',
                'message': "Great! Now please select your return flight:",
                'data': {
                    'flights': [
                        {
                            **flight,
                            'id': f'ret-{i}',
                            'flight_type': 'return',
                            'departure_city': flight['arrival_city'],
                            'arrival_city': flight['departure_city'],
                            'departure_airport': flight['arrival_airport'],
                            'arrival_airport': flight['departure_airport']
                        }
                        for i, flight in enumerate(mock_flights)
                    ]
                }
            })
        
        elif message_type == 'flight_select_inbound':
            # Process inbound flight selection and generate itinerary
            selected_flight_id = request_data.get('selected_flight_id')
            if not selected_flight_id:
                return jsonify({
                    'success': False,
                    'error': 'No flight selected',
                    'message': 'Please select a flight'
                }), 400
            
            # Extract the index from the flight ID (e.g., 'ret-0' -> 0)
            try:
                flight_index = int(selected_flight_id.split('-')[1])
                inbound_flight = mock_flights[flight_index]
            except (IndexError, ValueError):
                # If we can't parse the index, use the second flight
                inbound_flight = mock_flights[1]
            
            # Get the previously selected outbound flight from conversation data
            stored_outbound_flight = conversations[conversation_id]['data'].get('selectedOutboundFlight', mock_flights[0])
            
            # Get the trip planner state
            trip_planner_state = conversations[conversation_id]['data'].get('trip_planner_state', {})
            
            # Create graph instance
            graph = TripPlannerGraph()
            
            # Update state with selected flights
            state = {
                **trip_planner_state,
                "flights": [stored_outbound_flight, inbound_flight]
            }
            
            # Process the state to generate itinerary
            result = asyncio.run(graph.process(state))
            
            # Store the result in conversation data
            conversations[conversation_id]['data']['trip_planner_state'] = result
            
            # Add AI response to conversation
            conversations[conversation_id]['messages'].append({
                'id': int(time.time() * 1000) + 1,
                'text': "Your itinerary has been generated with your selected flights. Check the itinerary view for details.",
                'sender': 'ai',
                'timestamp': datetime.now().isoformat()
            })
            
            return jsonify({
                'success': True,
                'conversation_id': conversation_id,
                'type': 'generate_itinerary',
                'message': "Your itinerary has been generated with your selected flights. Check the itinerary view for details.",
                'data': {
                    'itinerary': result.get('final_itinerary', {})
                }
            })
        
        elif message_type == 'chat':
            # Create graph instance
            graph = TripPlannerGraph()
            
            # Initialize state with the user's message
            state = {
                "query": message,
                "raw_query": message,
                "metadata": None,  # Will be populated by the graph
                "is_valid": False,
                "next_question": None,
                "error": None,
                "thought": None,
                "action": None,
                "action_input": None,
                "observation": None,
                "nodes_to_call": [],
                "flights": [],
                "places": [],
                "restaurants": [],
                "hotel": {},
                "budget": {},
                "route": {}
            }
            
            # Process the query
            result = asyncio.run(graph.process(state))
            
            # Store the result in conversation data
            conversations[conversation_id]['data']['trip_planner_state'] = result
            
            # Add AI response to conversation
            conversations[conversation_id]['messages'].append({
                'id': int(time.time() * 1000) + 1,
                'text': result.get('next_question', 'I understand. How else can I help you?'),
                'sender': 'ai',
                'timestamp': datetime.now().isoformat()
            })
            
            return jsonify({
                'success': True,
                'conversation_id': conversation_id,
                'type': 'chat',
                'message': result.get('next_question', 'I understand. How else can I help you?')
            })
        
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid message type',
                'message': 'Please provide a valid message type'
            }), 400
            
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'An error occurred while processing your request'
        }), 500

@app.route('/api/map-key', methods=['GET'])
def get_map_key():
    google_maps_api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    if not google_maps_api_key:
        print('Google Maps API key is not configured')
        return jsonify({'error': 'Internal server error'}), 500
    
    return jsonify({'api_key': google_maps_api_key})

if __name__ == '__main__':
    # Run on port 8000 to match Node.js backend
    app.run(port=8000, debug=True) 