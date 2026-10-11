"""
weather_cli.py  -  BEGINNER TIER
Command-line weather app using OpenWeatherMap.

Run:  python weather_cli.py
"""

import weather_api as api


def show_weather(w):
    temp_c = w["temp_c"]
    temp_f = api.c_to_f(temp_c)
    feels_c = w["feels_c"]
    wind = w["wind_ms"]

    print()
    print("=" * 44)
    print(f"  Weather in {w['city']}, {w['country']}")
    print("=" * 44)
    print(f"  Condition   : {w['description']}")
    print(f"  Temperature : {temp_c:.1f} °C  /  {temp_f:.1f} °F")
    print(f"  Feels like  : {feels_c:.1f} °C  /  {api.c_to_f(feels_c):.1f} °F")
    print(f"  Humidity    : {w['humidity']} %")
    print(f"  Wind speed  : {wind:.1f} m/s  ({api.ms_to_kmh(wind):.1f} km/h)")
    print("=" * 44)
    print()


def main():
    print("--- Basic Weather App ---")
    print("Enter a city (e.g. Ahmedabad, Paris,FR) or a ZIP/PIN code (e.g. 380001 or 10001,US).")
    print("Type 'q' to quit.\n")

    while True:
        user_input = input("City / ZIP code: ").strip()

        if user_input.lower() in ("q", "quit", "exit"):
            print("Goodbye!")
            break

        # Input validation: reject empty input
        if not user_input:
            print("Error: input cannot be empty. Please enter a city name or ZIP code.\n")
            continue

        try:
            weather = api.get_current(user_input)
            show_weather(weather)
        except api.CityNotFoundError as e:
            print(f"Error: {e}\n")
        except api.InvalidApiKeyError as e:
            print(f"Error: {e}\n")
            break  # no point continuing with a bad key
        except api.NetworkError as e:
            print(f"Error: {e}\n")
        except api.WeatherError as e:
            print(f"Error: {e}\n")
        except ValueError as e:
            print(f"Error: {e}\n")


if __name__ == "__main__":
    main()
