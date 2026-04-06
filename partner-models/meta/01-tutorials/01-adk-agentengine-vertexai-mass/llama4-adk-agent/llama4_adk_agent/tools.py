import requests

def get_exchange_rate(currency_from, currency_to):
    """
    Fetches the current exchange rate between two currencies using the Frankfurter API.

    Args:
        currency_from (str): The ISO 4217 code for the source currency (e.g., 'USD').
        currency_to (str): The ISO 4217 code for the target currency (e.g., 'EUR').

    Returns:
        dict: A dictionary containing the exchange rate data on success, or an error message if the request fails.
              Example success: {"amount": 1.0, "base": "USD", "date": "2023-10-27", "rates": {"EUR": 0.95}}
              Example failure: {"error": "..."}

    Raises:
        requests.exceptions.RequestException: If the network request fails (handled by try-except).
    """
    try:
        url = f"https://api.frankfurter.app/latest"
        params = {
            "from": currency_from,
            "to": currency_to
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}
