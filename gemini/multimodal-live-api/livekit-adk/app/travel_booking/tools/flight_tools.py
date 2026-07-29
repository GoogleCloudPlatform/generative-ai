def search_flights(origin: str, destination: str, date: str) -> list[dict]:
    """Search for flights matching origin, destination, and date.
    
    Args:
        origin: Airport code or city name for the flight origin (e.g., 'SFO', 'San Francisco').
        destination: Airport code or city name for the flight destination (e.g., 'JFK', 'New York').
        date: Departure date in YYYY-MM-DD format.
    """
    print(f"[Tool: search_flights] Searching for flights from {origin} to {destination} on {date}")
    return [
        {
            "flight_id": "AA-123",
            "airline": "American Airlines",
            "origin": origin,
            "destination": destination,
            "date": date,
            "departure_time": "08:00 AM",
            "arrival_time": "11:30 AM",
            "price": 350.00
        },
        {
            "flight_id": "UA-456",
            "airline": "United Airlines",
            "origin": origin,
            "destination": destination,
            "date": date,
            "departure_time": "02:15 PM",
            "arrival_time": "05:45 PM",
            "price": 290.00
        },
        {
            "flight_id": "DL-789",
            "airline": "Delta Air Lines",
            "origin": origin,
            "destination": destination,
            "date": date,
            "departure_time": "07:30 PM",
            "arrival_time": "11:00 PM",
            "price": 310.00
        }
    ]

def book_flight(flight_id: str, passenger_name: str) -> dict:
    """Book a flight using the flight_id and passenger's name.
    
    Args:
        flight_id: Unique flight identifier (e.g., 'AA-123').
        passenger_name: Full name of the passenger booking the flight.
    """
    print(f"[Tool: book_flight] Booking flight {flight_id} for passenger {passenger_name}")
    import uuid
    booking_id = f"FL-{uuid.uuid4().hex[:8].upper()}"
    return {
        "booking_id": booking_id,
        "flight_id": flight_id,
        "passenger_name": passenger_name,
        "status": "CONFIRMED",
        "seat": "14B",
        "message": f"Flight {flight_id} successfully booked for {passenger_name}."
    }

def cancel_flight(booking_id: str) -> dict:
    """Cancel an existing flight booking.
    
    Args:
        booking_id: Unique booking identifier starting with 'FL-'.
    """
    print(f"[Tool: cancel_flight] Cancelling flight booking {booking_id}")
    return {
        "booking_id": booking_id,
        "status": "CANCELLED",
        "refund_amount": 250.00,
        "message": f"Flight booking {booking_id} has been successfully cancelled."
    }
