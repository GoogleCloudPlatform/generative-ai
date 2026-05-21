from travel_booking.tools.flight_tools import search_flights, book_flight, cancel_flight
from travel_booking.tools.hotel_tools import search_hotels, book_hotel, cancel_hotel

# ==================================================
# Flight Tools Tests
# ==================================================

def test_search_flights():
    results = search_flights(origin="SFO", destination="JFK", date="2026-06-10")
    assert isinstance(results, list)
    assert len(results) == 3
    for flight in results:
        assert "flight_id" in flight
        assert "airline" in flight
        assert flight["origin"] == "SFO"
        assert flight["destination"] == "JFK"
        assert flight["date"] == "2026-06-10"
        assert isinstance(flight["price"], float)

def test_book_flight():
    booking = book_flight(flight_id="UA-456", passenger_name="Kishore")
    assert isinstance(booking, dict)
    assert booking["flight_id"] == "UA-456"
    assert booking["passenger_name"] == "Kishore"
    assert booking["status"] == "CONFIRMED"
    assert booking["booking_id"].startswith("FL-")
    assert len(booking["booking_id"]) == 11  # "FL-" (3) + 8 characters of hex

def test_cancel_flight():
    cancellation = cancel_flight(booking_id="FL-12345678")
    assert isinstance(cancellation, dict)
    assert cancellation["booking_id"] == "FL-12345678"
    assert cancellation["status"] == "CANCELLED"
    assert cancellation["refund_amount"] == 250.00

# ==================================================
# Hotel Tools Tests
# ==================================================

def test_search_hotels():
    results = search_hotels(location="New York", checkin_date="2026-06-10", checkout_date="2026-06-15")
    assert isinstance(results, list)
    assert len(results) == 3
    for hotel in results:
        assert "hotel_id" in hotel
        assert "name" in hotel
        assert hotel["location"] == "New York"
        assert isinstance(hotel["price_per_night"], float)
        assert "rating" in hotel
        assert isinstance(hotel["amenities"], list)
        assert len(hotel["amenities"]) > 0

def test_book_hotel():
    booking = book_hotel(hotel_id="HT-GRAND", guest_name="Kishore")
    assert isinstance(booking, dict)
    assert booking["hotel_id"] == "HT-GRAND"
    assert booking["guest_name"] == "Kishore"
    assert booking["status"] == "CONFIRMED"
    assert booking["booking_id"].startswith("HT-")
    assert len(booking["booking_id"]) == 11  # "HT-" (3) + 8 characters of hex

def test_cancel_hotel():
    cancellation = cancel_hotel(booking_id="HT-12345678")
    assert isinstance(cancellation, dict)
    assert cancellation["booking_id"] == "HT-12345678"
    assert cancellation["status"] == "CANCELLED"
    assert cancellation["refund_amount"] == 150.00
