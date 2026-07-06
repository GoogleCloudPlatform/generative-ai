def search_hotels(location: str, checkin_date: str, checkout_date: str) -> list[dict]:
    """Search for hotels in a specific location for the given check-in and check-out dates.
    
    Args:
        location: City name or destination area (e.g., 'New York', 'Miami').
        checkin_date: Arrival date in YYYY-MM-DD format.
        checkout_date: Departure date in YYYY-MM-DD format.
    """
    print(f"[Tool: search_hotels] Searching for hotels in {location} from {checkin_date} to {checkout_date}")
    return [
        {
            "hotel_id": "HT-GRAND",
            "name": "The Grand Regency Hotel",
            "location": location,
            "price_per_night": 220.00,
            "rating": "4.8/5",
            "amenities": ["WiFi", "Pool", "Gym", "Breakfast Included"]
        },
        {
            "hotel_id": "HT-BUDGET",
            "name": "Comfort Inn & Suites",
            "location": location,
            "price_per_night": 95.00,
            "rating": "4.1/5",
            "amenities": ["WiFi", "Breakfast Included", "Free Parking"]
        },
        {
            "hotel_id": "HT-LUXE",
            "name": "Aura Palace & Resort",
            "location": location,
            "price_per_night": 450.00,
            "rating": "4.9/5",
            "amenities": ["WiFi", "Spa", "Private Beach", "Fine Dining", "Gym"]
        }
    ]

def book_hotel(hotel_id: str, guest_name: str) -> dict:
    """Book a hotel room for the guest.
    
    Args:
        hotel_id: Unique hotel identifier (e.g., 'HT-GRAND').
        guest_name: Full name of the guest staying at the hotel.
    """
    print(f"[Tool: book_hotel] Booking hotel {hotel_id} for guest {guest_name}")
    import uuid
    booking_id = f"HT-{uuid.uuid4().hex[:8].upper()}"
    return {
        "booking_id": booking_id,
        "hotel_id": hotel_id,
        "guest_name": guest_name,
        "status": "CONFIRMED",
        "room_type": "Deluxe King Room",
        "message": f"Hotel {hotel_id} successfully booked for {guest_name}."
    }

def cancel_hotel(booking_id: str) -> dict:
    """Cancel an existing hotel booking.
    
    Args:
        booking_id: Unique booking identifier starting with 'HT-'.
    """
    print(f"[Tool: cancel_hotel] Cancelling hotel booking {booking_id}")
    return {
        "booking_id": booking_id,
        "status": "CANCELLED",
        "refund_amount": 150.00,
        "message": f"Hotel booking {booking_id} has been successfully cancelled."
    }
