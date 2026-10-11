# Weather App (Task 4)

A Python weather application using the OpenWeatherMap free API.

- **Beginner tier:** `weather_cli.py` (command-line)
- **Advanced tier:** `weather_gui.py` (Tkinter GUI with icons, hourly + 5-day forecast, unit toggle, IP location)

## Project structure

```
weather_app/
├── weather_api.py     # shared API logic, error handling, unit conversion
├── weather_cli.py     # beginner: command-line app
├── weather_gui.py     # advanced: Tkinter GUI app
├── requirements.txt
├── .env.example       # copy to .env and add your key
└── README.md
```

## Setup

1. Get a free API key at https://openweathermap.org (Sign up > API keys). New keys can take up to ~2 hours to activate.
2. Copy `.env.example` to `.env` and paste your key:
   ```
   OPENWEATHER_API_KEY=abcd1234yourkey
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
   (On Linux, Tkinter may need: `sudo apt install python3-tk`)

## Run

```
python weather_cli.py     # beginner
python weather_gui.py     # advanced
```

## Input formats

| You type       | Meaning                                  |
|----------------|------------------------------------------|
| `Ahmedabad`    | city name                                |
| `Paris,FR`     | city + country code                      |
| `380001`       | ZIP/PIN code (defaults to India, `IN`)   |
| `10001,US`     | ZIP code + country code                  |

Change the default country in `weather_api.py` (`DEFAULT_COUNTRY`).

## Feature checklist

**Beginner**
- [x] Prompt for city or ZIP code
- [x] API call + JSON parsing
- [x] Temperature (°C and °F), humidity, condition, wind speed
- [x] Graceful errors: city not found, timeout/no network, invalid API key
- [x] Reject empty input

**Advanced**
- [x] GUI with input field, Get Weather button, results panel
- [x] Weather icons from OpenWeatherMap
- [x] Hourly forecast panel (3-hour steps)
- [x] 5-day daily forecast panel
- [x] Celsius / Fahrenheit toggle
- [x] (Bonus) IP-based location via ipinfo.io
- [x] Errors shown inside the GUI

## Notes

- The free API returns forecasts in 3-hour steps, so "hourly" shows the next few 3-hour slots. Change `slots` in `build_hourly()` (default 3) if you want more or fewer.
- Never upload your `.env` file to GitHub. Add `.env` to `.gitignore`.
