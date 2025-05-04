"""
Flight Booking API endpoint.

This module provides an API endpoint for booking flights using visible
browser automation to demonstrate the booking process.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import asyncio
import os
import logging
from datetime import datetime

# Import our visible flight booker
from services.stagehand_flight_booker import VisibleFlightBooker

# Mock classes for testing without dependencies
class MockFlightBooker:
    async def initialize(self):
        return {"status": "initialized"}
    
    async def book_flight(self, flight_info, passenger_info, num_people=1):
        # In a real implementation, this would use the actual flight booker
        return {
            "status": "success",
            "message": "Flight booking initiated successfully",
            "payment_url": "https://example.com/payment"
        }
    
    async def close(self):
        pass

# Define our request models
class PassengerInfo(BaseModel):
    first_name: str = Field(..., description="Passenger's first name")
    last_name: str = Field(..., description="Passenger's last name")
    email: str = Field(..., description="Contact email address")
    phone: str = Field(..., description="Contact phone number")
    date_of_birth: Optional[str] = Field(None, description="Date of birth in YYYY-MM-DD format")

class FlightInfo(BaseModel):
    airline: str = Field(..., description="Airline name (e.g., Delta, American)")
    flight_number: str = Field(..., description="Flight number (e.g., D394)")
    departure_time: str = Field(..., description="Departure time in ISO format (YYYY-MM-DD HH:MM:SS)")
    arrival_time: str = Field(..., description="Arrival time in ISO format (YYYY-MM-DD HH:MM:SS)")
    price: float = Field(..., description="Flight price")
    currency: str = Field("USD", description="Currency for the price")
    origin: str = Field(..., description="Origin airport or city code (e.g., SFO)")
    destination: str = Field(..., description="Destination airport or city code (e.g., JFK)")

class BookingRequest(BaseModel):
    flight_info: FlightInfo = Field(..., description="Information about the flight to book")
    passenger_info: PassengerInfo = Field(..., description="Information about the passenger")
    num_people: int = Field(1, description="Number of passengers to book for")

class BookingResponse(BaseModel):
    status: str = Field(..., description="Status of the booking (success, error, pending)")
    message: str = Field(..., description="Descriptive message about the booking status")
    payment_url: Optional[str] = Field(None, description="URL to complete payment, if booking was successful")
    booking_id: Optional[str] = Field(None, description="Unique identifier for this booking")
    error: Optional[str] = Field(None, description="Error message, if status is 'error'")

# Create the router
router = APIRouter(
    prefix="/api/flights",
    tags=["flights"],
    responses={404: {"description": "Not found"}},
)

# Update the background task to use visible automation
async def book_flight_task(booking_request: BookingRequest, booking_id: str):
    try:
        booker = VisibleFlightBooker()
        
        try:
            await booker.initialize()
            
            # Convert Pydantic models to dictionaries
            flight_info = booking_request.flight_info.dict()
            passenger_info = booking_request.passenger_info.dict()
            
            # Book the flight - this will show the browser automation
            result = await booker.book_flight(
                flight_info=flight_info,
                passenger_info=passenger_info,
                num_people=booking_request.num_people
            )
            
            # Store the result for retrieval later
            logging.info(f"Booking result for {booking_id}: {result}")
            
        finally:
            await booker.close()
            
    except Exception as e:
        logging.error(f"Error in booking task for {booking_id}: {str(e)}")

# Define our endpoint
@router.post("/book", response_model=BookingResponse)
async def book_flight(
    booking_request: BookingRequest,
    background_tasks: BackgroundTasks
):
    """
    Start an automated flight booking process.
    
    This endpoint initiates a flight booking process using the given flight and passenger
    information. The booking is performed in the background, and this endpoint returns
    immediately with a booking ID that can be used to check the status.
    """
    try:
        # Generate a booking ID
        # In a real implementation, we would use a more robust ID generation system
        import uuid
        booking_id = str(uuid.uuid4())
        
        # Start the booking process in the background
        background_tasks.add_task(book_flight_task, booking_request, booking_id)
        
        # Return an immediate response
        return BookingResponse(
            status="pending",
            message="Flight booking initiated successfully",
            booking_id=booking_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting booking process: {str(e)}"
        )

@router.get("/status/{booking_id}", response_model=BookingResponse)
async def get_booking_status(booking_id: str):
    """
    Check the status of a flight booking.
    
    This endpoint checks the status of a previously initiated flight booking process.
    """
    try:
        # In a real implementation, we would look up the booking status in a database
        # For this example, we'll always return a mock successful response
        
        return BookingResponse(
            status="success",
            message="Flight booking completed successfully",
            payment_url="https://example.com/payment",
            booking_id=booking_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking booking status: {str(e)}"
        ) 