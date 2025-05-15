import pytest
import json
from datetime import datetime, timedelta
from main import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_check(client):
    """Test the health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'ok'
    assert 'message' in data

def test_create_conversation(client):
    """Test creating a new conversation"""
    response = client.post('/conversations')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert 'conversation_id' in data
    return data['conversation_id']

def test_get_conversation(client):
    """Test retrieving a conversation"""
    # First create a conversation
    conv_id = test_create_conversation(client)
    
    # Then retrieve it
    response = client.get(f'/conversations/{conv_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert data['conversation_id'] == conv_id
    assert 'messages' in data

def test_chat_initialize(client):
    """Test initializing a chat"""
    response = client.post('/chat', json={
        'type': 'initialize',
        'message': '',
        'conversation_id': None
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert 'conversation_id' in data
    assert data['type'] == 'initialize'
    assert 'message' in data

def test_chat_info_complete(client):
    """Test chat with complete trip information"""
    # First initialize a conversation
    conv_id = test_create_conversation(client)
    
    # Send complete trip information
    response = client.post('/chat', json={
        'type': 'info',
        'message': 'I want to plan a 3-day trip to Paris from New York for 2 people. We love museums and local cuisine. Budget is $2000 per person.',
        'conversation_id': conv_id
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert data['type'] == 'chat'
    assert 'message' in data
    assert 'data' in data
    assert 'metadata' in data['data']

def test_chat_info_incomplete(client):
    """Test chat with incomplete trip information"""
    conv_id = test_create_conversation(client)
    
    response = client.post('/chat', json={
        'type': 'info',
        'message': 'I want to go to Paris',
        'conversation_id': conv_id
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert data['type'] == 'chat'
    assert 'message' in data
    assert 'data' in data
    assert not data['data']['is_valid']  # Should be invalid due to missing info

def test_chat_info_incomplete_validation(client):
    """Test that the API asks back for missing information when incomplete trip details are provided."""
    conv_id = test_create_conversation(client)
    
    response = client.post('/chat', json={
        'type': 'info',
        'message': 'I want to go to Paris',
        'conversation_id': conv_id
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert data['type'] == 'chat'
    assert 'message' in data
    assert 'data' in data
    assert not data['data']['is_valid']  # Should be invalid due to missing info
    assert 'next_question' in data['data']  # API should ask back for missing info

def test_flight_selection(client):
    """Test the flight selection process"""
    # First get a conversation with complete info
    conv_id = test_create_conversation(client)
    
    # Send complete trip info
    response = client.post('/chat', json={
        'type': 'info',
        'message': 'I want to plan a 3-day trip to Paris from New York for 2 people. We love museums and local cuisine. Budget is $2000 per person.',
        'conversation_id': conv_id
    })
    data = json.loads(response.data)
    
    # Select outbound flight
    response = client.post('/chat', json={
        'type': 'flight_select_outbound',
        'message': '',
        'conversation_id': conv_id,
        'data': {'selected_flight_id': 'dep-0'}
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert data['type'] == 'flight_search_inbound'
    assert 'flights' in data['data']
    
    # Select inbound flight
    response = client.post('/chat', json={
        'type': 'flight_select_inbound',
        'message': '',
        'conversation_id': conv_id,
        'data': {'selected_flight_id': 'ret-0'}
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert data['type'] == 'generate_itinerary'
    assert 'itinerary' in data['data']

def test_error_handling(client):
    """Test error handling in various scenarios"""
    # Test invalid message type
    response = client.post('/chat', json={
        'type': 'invalid_type',
        'message': 'test',
        'conversation_id': None
    })
    assert response.status_code == 400
    data = json.loads(response.data)
    assert not data['success']
    assert 'error' in data
    
    # Test invalid conversation ID
    response = client.get('/conversations/invalid_id')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert not data['success']
    assert 'error' in data

def test_map_key_endpoint(client):
    """Test the map key endpoint"""
    response = client.get('/api/map-key')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'api_key' in data

def test_conversation_flow(client):
    """Test a complete conversation flow"""
    # Initialize conversation
    conv_id = test_create_conversation(client)
    
    # Send initial query
    response = client.post('/chat', json={
        'type': 'info',
        'message': 'I want to plan a trip to Paris',
        'conversation_id': conv_id
    })
    data = json.loads(response.data)
    assert data['success'] == True
    
    # Send follow-up with more details
    response = client.post('/chat', json={
        'type': 'chat',
        'message': 'I want to go for 3 days with my partner',
        'conversation_id': conv_id
    })
    data = json.loads(response.data)
    assert data['success'] == True
    
    # Send preferences
    response = client.post('/chat', json={
        'type': 'chat',
        'message': 'We love museums and local cuisine',
        'conversation_id': conv_id
    })
    data = json.loads(response.data)
    assert data['success'] == True
    
    # Verify conversation history
    response = client.get(f'/conversations/{conv_id}')
    data = json.loads(response.data)
    assert data['success'] == True
    assert len(data['messages']) > 0 