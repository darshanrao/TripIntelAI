from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Flight(BaseModel):
    airline: str
    flight_number: str
    departure_time: datetime
    arrival_time: datetime
    price: float
    currency: str = "USD"

class Hotel(BaseModel):
    name: str
    rating: float
    price_per_night: float
    currency: str = "USD"
    location: str
    amenities: List[str] = []
    place_id: Optional[str] = None

class Place(BaseModel):
    """Model for a place/attraction"""
    name: str
    description: str
    rating: float
    price: float
    location: str
    category: str
    place_id: Optional[str] = None

class Restaurant(BaseModel):
    """Model for a restaurant"""
    name: str
    cuisine: str
    rating: float
    price_level: int  # 1-4
    location: str
    description: str
    place_id: Optional[str] = None

class Budget(BaseModel):
    flights_total: float
    hotel_total: float
    daily_food_estimate: float
    activities_estimate: float
    total: float
    currency: str = "USD"

class TripMetadata(BaseModel):
    source: str
    destination: str
    start_date: datetime
    end_date: datetime
    num_people: int
    preferences: List[str] = []

class TripData(BaseModel):
    metadata: TripMetadata
    flights: List[Flight] = []
    hotel: Optional[Hotel] = None
    places: List[Place] = []
    restaurants: List[Restaurant] = []
    budget: Optional[Budget] = None 