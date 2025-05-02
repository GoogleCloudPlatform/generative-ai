# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import requests
import json
import os
from google.cloud import secretmanager

def get_secret(secret_id):
    """Get secret from Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.environ.get('PROJECT_ID')
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def get_weather(request):
    """Responds to an HTTP request with weather data."""

    # Get location from request parameters (e.g., city, lat/lon)
    city = request.args.get('city')
    lat = request.args.get('lat')
    lon = request.args.get('lon')

    if not city and not (lat and lon):
        return "Please provide either 'city' or 'lat' and 'lon' parameters.", 400

    try:
        api_key = get_secret('OPENWEATHER_API_KEY')
    except Exception as e:
        return f"Error fetching API key from Secret Manager: {e}", 500

    if not api_key:
        return "API key not configured.", 500

    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        'appid': api_key,
        'units': 'metric'  # Or 'imperial' for Fahrenheit
    }

    if city:
        params['q'] = city
    elif lat and lon:
        params['lat'] = lat
        params['lon'] = lon

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        weather_data = response.json()

        # Construct the response with transformed data
        custom_weather_response = {
            "city": weather_data['name'],
            "temperature": int((weather_data['main']['temp'])),
            "description": weather_data['weather'][0]['description'],
            "humidity": weather_data['main']['humidity'],
        }

        return json.dumps(custom_weather_response), 200, {'Content-Type': 'application/json'}
        # return json.dumps(weather_data), 200, {'Content-Type': 'application/json'}

    except requests.exceptions.HTTPError as e:
        return f"Error from OpenWeatherMap API: {e}", e.response.status_code
    except requests.exceptions.RequestException as e:
        return f"Error connecting to OpenWeatherMap API: {e}", 500
    except Exception as e:
        return f"An unexpected error occurred: {e}", 500


if __name__ == '__main__':
    # Example of local testing (optional)
    # To run locally: python main.py
    class MockRequest:
        def __init__(self, args):
            self.args = args

    mock_request_city = MockRequest({'city': 'London'})
    mock_request_latlon = MockRequest({'lat': '51.5', 'lon': '-0.12'})

    city_weather, status_city, headers_city = get_weather(mock_request_city)
    print("Weather for London:")
    print(city_weather)

    latlon_weather, status_latlon, headers_latlon = get_weather(mock_request_latlon)
    print("\nWeather for Lat/Lon (London):")
    print(latlon_weather)