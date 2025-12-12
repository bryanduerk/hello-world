# Shared Travel Planner

A starter FastAPI service for collaboratively building itineraries. Users can register/login, create trips with flights and hotels, and share trips with other accounts.

## Features
- Email/password registration with hashed credentials and JWT login tokens
- Create trips with optional start/end dates
- Add flights (airline, airports, times) and hotels (city, check-in/out) to a trip
- Share trips with other registered users for read/write access
- SQLite persistence by default

## Getting started
1. Install dependencies (recommend a virtual environment):
   ```bash
   pip install -r requirements.txt
   ```
2. Run the API server:
   ```bash
   uvicorn app.main:app --reload
   ```
3. Open the interactive docs at `http://127.0.0.1:8000/docs` to try the endpoints.

## API highlights
- `POST /auth/register` – create an account
- `POST /auth/login` – obtain an access token (send `username` + `password` form fields)
- `POST /trips` – create a trip with optional flights/hotels payloads
- `GET /trips` and `GET /trips/{trip_id}` – view trips you own or that are shared with you
- `POST /trips/{trip_id}/share` – share a trip with another registered email
- `POST /trips/{trip_id}/flights` and `POST /trips/{trip_id}/hotels` – append items to an existing trip

Use the `Authorization: Bearer <token>` header for all `/trips` endpoints.
