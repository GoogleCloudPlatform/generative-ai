def get_user_preferences(user_id: str) -> dict:
    """Retrieve user preferences, past purchases, or specific constraints."""
    print(f"Tool: get_user_preferences called for user_id={user_id}")
    return {
        "user_id": user_id,
        "preferences": "Prefers sustainable brands, minimalist design, and budget range ₹20k-₹50k.",
        "past_purchases": "Purchased sustainable sneakers in 2023."
    }
