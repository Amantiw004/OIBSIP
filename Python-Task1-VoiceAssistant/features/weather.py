"""
weather.py - "Fetch and read out live weather updates using a weather API"
(OpenWeatherMap free tier).

Requires OPENWEATHER_API_KEY in your .env file.
Get a free key at: https://openweathermap.org/api
"""

import os

import requests

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


def get_weather_report(city: str) -> str:
    """Return a spoken-friendly weather summary for `city`, or an error message."""
    api_key = os.getenv("OPENWEATHER_API_KEY")

    if not api_key or api_key.strip() == "" or "your_openweathermap" in api_key:
        return (
            "The weather feature needs an OpenWeatherMap API key. "
            "Please add OPENWEATHER_API_KEY to your dot env file."
        )

    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",  # Celsius. Use "imperial" for Fahrenheit.
    }

    try:
        response = requests.get(OPENWEATHER_URL, params=params, timeout=8)
    except requests.exceptions.RequestException as e:
        return f"I couldn't reach the weather service. Please check your internet connection."

    if response.status_code == 401:
        return "The weather API key seems invalid. Please double-check it in your dot env file."
    if response.status_code == 404:
        return f"I couldn't find weather data for {city}. Could you check the city name?"
    if response.status_code != 200:
        return "The weather service returned an unexpected error. Please try again later."

    data = response.json()
    try:
        description = data["weather"][0]["description"]
        temp = round(data["main"]["temp"])
        feels_like = round(data["main"]["feels_like"])
        humidity = data["main"]["humidity"]
    except (KeyError, IndexError):
        return "I received an unexpected response from the weather service."

    return (
        f"The weather in {city.title()} is currently {description}, "
        f"with a temperature of {temp} degrees Celsius, feeling like "
        f"{feels_like} degrees. Humidity is at {humidity} percent."
    )
