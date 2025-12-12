from datetime import datetime
from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, SQLModel, select

from .auth import create_access_token, get_current_user, get_password_hash, verify_password
from .db import engine, get_session
from .models import Flight, Hotel, Trip, TripShare, User
from .schemas import FlightCreate, HotelCreate, ShareRequest, Token, TripCreate, TripRead, UserCreate, UserRead

app = FastAPI(title="Shared Travel Planner")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    SQLModel.metadata.create_all(engine)


@app.post("/auth/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_create: UserCreate, session: Session = Depends(get_session)) -> UserRead:
    existing_user = session.exec(select(User).where(User.email == user_create.email)).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    hashed_password = get_password_hash(user_create.password)
    user = User(email=user_create.email, hashed_password=hashed_password)
    session.add(user)
    session.commit()
    session.refresh(user)
    return UserRead(id=user.id, email=user.email)


@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)) -> Token:
    user = session.exec(select(User).where(User.email == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    access_token = create_access_token({"sub": str(user.id)})
    return Token(access_token=access_token)


@app.post("/trips", response_model=TripRead, status_code=status.HTTP_201_CREATED)
def create_trip(trip_create: TripCreate, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)) -> TripRead:
    trip = Trip(
        name=trip_create.name,
        owner_id=current_user.id,
        start_date=trip_create.start_date,
        end_date=trip_create.end_date,
    )
    session.add(trip)
    session.commit()
    session.refresh(trip)

    flights = [
        Flight(
            trip_id=trip.id,
            airline=flight.airline,
            departure_airport=flight.departure_airport,
            arrival_airport=flight.arrival_airport,
            departure_time=flight.departure_time,
            arrival_time=flight.arrival_time,
        )
        for flight in trip_create.flights
    ]
    hotels = [
        Hotel(
            trip_id=trip.id,
            name=hotel.name,
            city=hotel.city,
            check_in=hotel.check_in,
            check_out=hotel.check_out,
        )
        for hotel in trip_create.hotels
    ]
    session.add_all(flights + hotels)
    session.commit()

    return _trip_to_read(trip, flights, hotels, [])


@app.get("/trips", response_model=List[TripRead])
def list_trips(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)) -> List[TripRead]:
    owned_trips = session.exec(select(Trip).where(Trip.owner_id == current_user.id)).all()
    shared_trip_ids = session.exec(select(TripShare.trip_id).where(TripShare.user_id == current_user.id)).all()
    shared_trips = []
    if shared_trip_ids:
        shared_trips = session.exec(select(Trip).where(Trip.id.in_(shared_trip_ids))).all()

    trips = owned_trips + [trip for trip in shared_trips if trip not in owned_trips]

    return [_trip_to_read(trip, _fetch_flights(session, trip.id), _fetch_hotels(session, trip.id), _fetch_share_ids(session, trip.id)) for trip in trips]


@app.get("/trips/{trip_id}", response_model=TripRead)
def get_trip(trip_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)) -> TripRead:
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    if trip.owner_id != current_user.id and not _user_has_access(session, current_user.id, trip_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this trip")

    return _trip_to_read(trip, _fetch_flights(session, trip_id), _fetch_hotels(session, trip_id), _fetch_share_ids(session, trip_id))


@app.post("/trips/{trip_id}/share", status_code=status.HTTP_204_NO_CONTENT)
def share_trip(trip_id: int, share_request: ShareRequest, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)) -> None:
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    if trip.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can share the trip")

    target_user = session.exec(select(User).where(User.email == share_request.email)).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User to share with was not found")
    if target_user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot share a trip with yourself")

    existing_share = session.exec(
        select(TripShare).where(TripShare.trip_id == trip_id, TripShare.user_id == target_user.id)
    ).first()
    if existing_share:
        return

    share = TripShare(trip_id=trip_id, user_id=target_user.id, created_at=datetime.utcnow())
    session.add(share)
    session.commit()


@app.post("/trips/{trip_id}/flights", response_model=TripRead)
def add_flight(
    trip_id: int,
    flight: FlightCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TripRead:
    _ensure_trip_access(session, current_user.id, trip_id)
    flight_row = Flight(trip_id=trip_id, **flight.dict())
    session.add(flight_row)
    session.commit()
    return _trip_to_read(
        session.get(Trip, trip_id),
        _fetch_flights(session, trip_id),
        _fetch_hotels(session, trip_id),
        _fetch_share_ids(session, trip_id),
    )


@app.post("/trips/{trip_id}/hotels", response_model=TripRead)
def add_hotel(
    trip_id: int,
    hotel: HotelCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TripRead:
    _ensure_trip_access(session, current_user.id, trip_id)
    hotel_row = Hotel(trip_id=trip_id, **hotel.dict())
    session.add(hotel_row)
    session.commit()
    return _trip_to_read(
        session.get(Trip, trip_id),
        _fetch_flights(session, trip_id),
        _fetch_hotels(session, trip_id),
        _fetch_share_ids(session, trip_id),
    )


def _fetch_flights(session: Session, trip_id: int) -> List[Flight]:
    return session.exec(select(Flight).where(Flight.trip_id == trip_id)).all()


def _fetch_hotels(session: Session, trip_id: int) -> List[Hotel]:
    return session.exec(select(Hotel).where(Hotel.trip_id == trip_id)).all()


def _fetch_share_ids(session: Session, trip_id: int) -> List[int]:
    return [share.user_id for share in session.exec(select(TripShare).where(TripShare.trip_id == trip_id)).all()]


def _user_has_access(session: Session, user_id: int, trip_id: int) -> bool:
    share = session.exec(select(TripShare).where(TripShare.trip_id == trip_id, TripShare.user_id == user_id)).first()
    return share is not None


def _ensure_trip_access(session: Session, user_id: int, trip_id: int) -> None:
    trip = session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    if trip.owner_id != user_id and not _user_has_access(session, user_id, trip_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this trip")


def _trip_to_read(trip: Trip, flights: List[Flight], hotels: List[Hotel], shared_ids: List[int]) -> TripRead:
    return TripRead(
        id=trip.id,
        name=trip.name,
        owner_id=trip.owner_id,
        start_date=trip.start_date,
        end_date=trip.end_date,
        flights=flights,
        hotels=hotels,
        shared_with_user_ids=shared_ids,
    )
