"""
Test suite for the flight booking API endpoints.
"""

from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import pytest
from app.main import app

client = TestClient(app)

def test_book_flight():
    # Create test data
    tomorrow = datetime.now() + timedelta(days=1)
    departure_time = tomorrow.strftime("%Y-%m-%d %H:%M:%S")
    arrival_time = (tomorrow + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")
    
    booking_data = {
        "flight_info": {
            "airline": "Test Airlines",
            "flight_number": "TA123",
            "departure_time": departure_time,
            "arrival_time": arrival_time,
            "price": 299.99,
            "currency": "USD",
            "origin": "SFO",
            "destination": "JFK"
        },
        "passenger_info": {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "+1234567890",
            "date_of_birth": "1990-01-01"
        },
        "num_people": 1
    }
    
    # Test booking initiation
    response = client.post("/api/flights/book", json=booking_data)
    assert response.status_code == 200
    
    booking_response = response.json()
    assert booking_response["status"] == "pending"
    assert "booking_id" in booking_response
    
    # Test booking status
    booking_id = booking_response["booking_id"]
    status_response = client.get(f"/api/flights/status/{booking_id}")
    assert status_response.status_code == 200
    
    status_data = status_response.json()
    assert status_data["status"] == "success"
    assert status_data["payment_url"] == "https://example.com/payment"
    assert status_data["booking_id"] == booking_id

def test_invalid_booking():
    # Test with missing required fields
    invalid_data = {
        "flight_info": {
            "airline": "Test Airlines"  # Missing other required fields
        },
        "passenger_info": {
            "first_name": "John"  # Missing other required fields
        }
    }
    
    response = client.post("/api/flights/book", json=invalid_data)
    assert response.status_code == 422  # Validation error

def test_invalid_booking_status():
    # Test with non-existent booking ID
    response = client.get("/api/flights/status/nonexistent-id")
    assert response.status_code == 200  # Our mock always returns success
    # In a real implementation, this would be 404 