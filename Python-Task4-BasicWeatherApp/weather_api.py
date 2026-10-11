"""
weather_api.py
Shared helper functions for the Weather App (CLI + GUI).

Talks to the OpenWeatherMap free-tier API:
  * Current weather : /data/2.5/weather
  * 5-day forecast  : /data/2.5/forecast   (3-hour steps)
and (bonus) ipinfo.io for automatic location detection.
"""

import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = "https://api.openweathermap.org/data/2.5"
ICON_URL = "https://openweathermap.org/img/wn/{code}@2x.png"
IPINFO_URL = "https://ipinfo.io/json"
TIMEOUT = 10  # seconds
DEFAULT_COUNTRY = "IN"  # used when the user types only a ZIP / PIN code


# ----------------------------------------------------------------------
# Custom exceptions (so the UI can show friendly messages)
# ----------------------------------------------------------------------
class WeatherError(Exception):
    """Generic weather-related error."""


class CityNotFoundError(WeatherError):
    pass


class InvalidApiKeyError(WeatherError):
    pass


class NetworkError(WeatherError):
    pass


# ----------------------------------------------------------------------
# API key handling (reads .env file or environment variable)
# ----------------------------------------------------------------------
def _load_dotenv():
    env_file = Path(__file__).with_name(".env")
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def get_api_key():
    key = os.environ.get("OPENWEATHER_API_KEY", "").strip()
    if not key or key == "your_api_key_here":
        raise InvalidApiKeyError(
            "API key missing. Put your OpenWeatherMap key in the .env file "
            "(OPENWEATHER_API_KEY=...)."
        )
    return key


# ----------------------------------------------------------------------
# Input handling
# ----------------------------------------------------------------------
def build_query(user_input):
    """
    Turn user text into API parameters.
      "Ahmedabad"        -> {"q": "Ahmedabad"}
      "Paris,FR"         -> {"q": "Paris,FR"}
      "380001"           -> {"zip": "380001,IN"}   (default country)
      "10001,US"         -> {"zip": "10001,US"}
    """
    text = (user_input or "").strip()
    if not text:
        raise ValueError("Please enter a city name or ZIP code.")

    parts = [p.strip() for p in text.split(",")]
    first = parts[0].replace(" ", "").replace("-", "")
    if first.isdigit():
        country = parts[1].upper() if len(parts) > 1 and parts[1] else DEFAULT_COUNTRY
        return {"zip": f"{parts[0]},{country}"}
    return {"q": text}


# ----------------------------------------------------------------------
# Low-level request with graceful error handling
# ----------------------------------------------------------------------
def _get(endpoint, params):
    params = {**params, "appid": get_api_key(), "units": "metric"}
    try:
        resp = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=TIMEOUT)
    except requests.exceptions.Timeout:
        raise NetworkError("The request timed out. Please try again.")
    except requests.exceptions.ConnectionError:
        raise NetworkError("No internet connection. Please check your network.")
    except requests.exceptions.RequestException as exc:
        raise NetworkError(f"Network error: {exc}")

    if resp.status_code == 401:
        raise InvalidApiKeyError(
            "Invalid API key. Check your key (new keys can take up to 2 hours to activate)."
        )
    if resp.status_code == 404:
        raise CityNotFoundError("City / ZIP code not found. Please check the spelling.")
    if resp.status_code == 429:
        raise WeatherError("Too many requests (limit 60/min). Wait a moment and retry.")
    if resp.status_code != 200:
        raise WeatherError(f"Weather service error (HTTP {resp.status_code}).")

    try:
        return resp.json()
    except ValueError:
        raise WeatherError("Received an invalid response from the weather service.")


# ----------------------------------------------------------------------
# Public data functions
# ----------------------------------------------------------------------
def get_current(user_input):
    """Return a clean dict with current weather. Temperatures are in Celsius."""
    data = _get("weather", build_query(user_input))
    weather = (data.get("weather") or [{}])[0]
    main = data.get("main", {})
    return {
        "city": data.get("name") or "Unknown",
        "country": data.get("sys", {}).get("country", ""),
        "temp_c": main.get("temp"),
        "feels_c": main.get("feels_like"),
        "humidity": main.get("humidity"),
        "description": weather.get("description", "n/a").title(),
        "icon": weather.get("icon"),
        "wind_ms": data.get("wind", {}).get("speed", 0),
        "lat": data.get("coord", {}).get("lat"),
        "lon": data.get("coord", {}).get("lon"),
    }


def get_forecast(lat, lon):
    """Raw 5-day / 3-hour forecast for a coordinate."""
    return _get("forecast", {"lat": lat, "lon": lon})


def _local_dt(ts, tz_offset):
    return datetime.fromtimestamp(ts + tz_offset, tz=timezone.utc)


def build_hourly(forecast, slots=3):
    """
    First few forecast slots. The free API gives 3-hour steps, so
    2 slots ~ next 6 hours, 3 slots ~ next 9 hours (change `slots` if you like).
    """
    tz = forecast.get("city", {}).get("timezone", 0)
    result = []
    for item in forecast.get("list", [])[:slots]:
        local = _local_dt(item["dt"], tz)
        w = item["weather"][0]
        result.append(
            {
                "label": local.strftime("%I:%M %p").lstrip("0"),
                "temp_c": item["main"]["temp"],
                "description": w["description"].title(),
                "icon": w["icon"],
                "rain_chance": round(item.get("pop", 0) * 100),
            }
        )
    return result


def build_daily(forecast, days=5):
    """Group the 3-hour slots by local date -> min/max temp + midday icon."""
    tz = forecast.get("city", {}).get("timezone", 0)
    buckets = {}
    for item in forecast.get("list", []):
        local = _local_dt(item["dt"], tz)
        buckets.setdefault(local.date(), []).append((local, item))

    today = _local_dt(time.time(), tz).date()
    result = []
    for day in sorted(buckets):
        if day == today:
            continue
        entries = buckets[day]
        temps = [it["main"]["temp"] for _, it in entries]
        midday = min(entries, key=lambda e: abs(e[0].hour - 12))[1]
        w = midday["weather"][0]
        result.append(
            {
                "label": day.strftime("%a, %d %b"),
                "min_c": min(temps),
                "max_c": max(temps),
                "description": w["description"].title(),
                "icon": w["icon"],
            }
        )
    return result[:days]


def download_icon(code):
    """Download an OpenWeatherMap icon (PNG bytes). Returns None if it fails."""
    if not code:
        return None
    try:
        resp = requests.get(ICON_URL.format(code=code), timeout=TIMEOUT)
        if resp.status_code == 200:
            return resp.content
    except requests.exceptions.RequestException:
        pass
    return None


def get_location_from_ip():
    """(Bonus) Detect the user's city from their IP using ipinfo.io (free tier)."""
    try:
        resp = requests.get(IPINFO_URL, timeout=TIMEOUT)
        resp.raise_for_status()
        info = resp.json()
    except requests.exceptions.RequestException:
        raise NetworkError("Could not detect your location. Type a city instead.")
    except ValueError:
        raise WeatherError("Could not read location data.")

    city = info.get("city")
    if not city:
        raise WeatherError("Location could not be determined. Type a city instead.")
    country = info.get("country", "")
    return f"{city},{country}" if country else city


# ----------------------------------------------------------------------
# Unit helpers
# ----------------------------------------------------------------------
def c_to_f(c):
    return c * 9 / 5 + 32


def ms_to_kmh(v):
    return v * 3.6


def ms_to_mph(v):
    return v * 2.23694
