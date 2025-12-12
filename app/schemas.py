from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @validator("password")
    def password_length(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return value


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    id: int
    email: EmailStr


class FlightCreate(BaseModel):
    airline: str
    departure_airport: str
    arrival_airport: str
    departure_time: datetime
    arrival_time: datetime


class HotelCreate(BaseModel):
    name: str
    city: str
    check_in: date
    check_out: date


class TripBase(BaseModel):
    name: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class TripCreate(TripBase):
    flights: List[FlightCreate] = []
    hotels: List[HotelCreate] = []


class FlightRead(FlightCreate):
    id: int


class HotelRead(HotelCreate):
    id: int


class TripRead(TripBase):
    id: int
    owner_id: int
    flights: List[FlightRead]
    hotels: List[HotelRead]
    shared_with_user_ids: List[int]


class ShareRequest(BaseModel):
    email: EmailStr
