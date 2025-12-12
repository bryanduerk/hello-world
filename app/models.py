from datetime import date, datetime
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class TripShare(SQLModel, table=True):
    trip_id: Optional[int] = Field(default=None, foreign_key="trip.id", primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    trip: "Trip" = Relationship(back_populates="shared_with")
    user: "User" = Relationship(back_populates="shared_trips")


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    trips: List["Trip"] = Relationship(back_populates="owner")
    shared_trips: List[TripShare] = Relationship(back_populates="user")


class Trip(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    owner_id: int = Field(foreign_key="user.id")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    owner: User = Relationship(back_populates="trips")
    flights: List["Flight"] = Relationship(back_populates="trip")
    hotels: List["Hotel"] = Relationship(back_populates="trip")
    shared_with: List[TripShare] = Relationship(back_populates="trip")


class Flight(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    trip_id: int = Field(foreign_key="trip.id")
    airline: str
    departure_airport: str
    arrival_airport: str
    departure_time: datetime
    arrival_time: datetime

    trip: Trip = Relationship(back_populates="flights")


class Hotel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    trip_id: int = Field(foreign_key="trip.id")
    name: str
    city: str
    check_in: date
    check_out: date

    trip: Trip = Relationship(back_populates="hotels")
