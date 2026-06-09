#!/usr/bin/env python3
"""A smart weather app with global coverage and simple future outlooks."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from typing import Any, Dict, List
from urllib import error, parse, request

WEATHER_CODES: Dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}


def fetch_json(url: str) -> Dict[str, Any]:
    req = request.Request(url, headers={"User-Agent": "smart-weather-app/1.0"})
    with request.urlopen(req, timeout=15) as response:
        return json.load(response)


def describe_weather(code: int, is_day: int | None = None) -> str:
    base = WEATHER_CODES.get(code, "Unknown conditions")
    if is_day is not None and is_day == 0:
        return f"{base} at night"
    return base


def geocode_city(city: str) -> Dict[str, Any]:
    encoded_city = parse.quote(city)
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_city}&count=1&language=en&format=json"
    data = fetch_json(url)
    results = data.get("results") or []
    if not results:
        raise ValueError(f"No location found for '{city}'. Try a more specific city name.")

    place = results[0]
    return {
        "name": place.get("name", city),
        "country": place.get("country", ""),
        "admin1": place.get("admin1", ""),
        "latitude": place["latitude"],
        "longitude": place["longitude"],
    }


def get_weather_forecast(latitude: float, longitude: float, days: int = 5) -> Dict[str, Any]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m,is_day",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max",
        "forecast_days": days,
        "timezone": "auto",
    }
    url = f"https://api.open-meteo.com/v1/forecast?{parse.urlencode(params)}"
    return fetch_json(url)


def build_smart_insight(current: Dict[str, Any], daily: List[Dict[str, Any]]) -> str:
    temp = current.get("temperature_2m", 0)
    humidity = current.get("relative_humidity_2m", 0)
    precipitation = current.get("precipitation", 0)
    wind = current.get("wind_speed_10m", 0)
    weather_code = current.get("weather_code", 0)

    if precipitation > 1.0:
        advice = "Rain is falling now, so bring an umbrella and keep a light layer ready."
    elif temp < 8:
        advice = "It is chilly, so wear a warm jacket and keep your hands covered."
    elif temp > 29:
        advice = "It is very warm, so stay hydrated and limit direct sun exposure."
    elif humidity > 80:
        advice = "Humidity is high, so expect a muggy feel and dress lightly."
    elif wind > 20:
        advice = "The wind is strong, so secure loose items and wear a windproof layer."
    elif weather_code in {95, 96, 99}:
        advice = "Storms are possible, so keep indoor plans ready."
    else:
        advice = "Conditions look comfortable, and the day is good for a walk or outdoor plans."

    if daily:
        tomorrow = daily[0]
        if tomorrow.get("precipitation_probability_max", 0) > 60:
            advice += " Tomorrow looks wetter, so plan for rain."
        elif tomorrow.get("temperature_2m_max", temp) > temp + 4:
            advice += " The next few days look warmer."
        elif tomorrow.get("temperature_2m_max", temp) < temp - 4:
            advice += " A cooler spell is on the way."

    return advice


def build_future_outlook(daily: List[Dict[str, Any]]) -> str:
    if not daily:
        return "No forecast data is currently available."

    first = daily[0]
    second = daily[1] if len(daily) > 1 else first
    third = daily[2] if len(daily) > 2 else first

    if first.get("precipitation_probability_max", 0) > 60:
        return "Rain is likely over the next day or two, so keep a backup plan ready."

    if first.get("temperature_2m_max", 0) > second.get("temperature_2m_max", 0) and first.get("temperature_2m_max", 0) > third.get("temperature_2m_max", 0):
        return "Temperatures are expected to rise over the next few days."

    if first.get("temperature_2m_max", 0) < second.get("temperature_2m_max", 0) and first.get("temperature_2m_max", 0) < third.get("temperature_2m_max", 0):
        return "The weather should stay mild and stable over the next few days."

    return "The next few days look mixed, with changing conditions that are worth watching."


def print_report(location: Dict[str, Any], weather_data: Dict[str, Any], days: int) -> None:
    current = weather_data.get("current", {})
    daily = weather_data.get("daily", {}).get("time", [])
    daily_weather_codes = weather_data.get("daily", {}).get("weather_code", [])
    daily_highs = weather_data.get("daily", {}).get("temperature_2m_max", [])
    daily_lows = weather_data.get("daily", {}).get("temperature_2m_min", [])
    daily_precip = weather_data.get("daily", {}).get("precipitation_probability_max", [])

    print(f"Weather for {location['name']}, {location['country']}")
    print("=" * 42)
    print(f"Current conditions: {describe_weather(int(current.get('weather_code', 0)), current.get('is_day'))}")
    print(f"Temperature: {current.get('temperature_2m', 'n/a')}°C")
    print(f"Feels like: {current.get('apparent_temperature', 'n/a')}°C")
    print(f"Humidity: {current.get('relative_humidity_2m', 'n/a')}%")
    print(f"Wind: {current.get('wind_speed_10m', 'n/a')} km/h")
    print(f"Precipitation: {current.get('precipitation', 'n/a')} mm")
    print(f"Smart insight: {build_smart_insight(current, _daily_forecast_rows(weather_data, days))}")
    print()
    print(f"Forecast for the next {days} days")
    print("-" * 42)

    for index, day in enumerate(daily[:days]):
        day_label = datetime.fromisoformat(day).strftime("%a %d %b")
        code = daily_weather_codes[index] if index < len(daily_weather_codes) else 0
        high = daily_highs[index] if index < len(daily_highs) else "n/a"
        low = daily_lows[index] if index < len(daily_lows) else "n/a"
        chance = daily_precip[index] if index < len(daily_precip) else "n/a"
        print(f"{day_label}: {describe_weather(int(code))} | High {high}°C | Low {low}°C | Rain {chance}%")

    print()
    print(f"Future outlook: {build_future_outlook(_daily_forecast_rows(weather_data, days))}")


def _daily_forecast_rows(weather_data: Dict[str, Any], days: int) -> List[Dict[str, Any]]:
    daily = weather_data.get("daily", {})
    rows: List[Dict[str, Any]] = []
    for index in range(min(days, len(daily.get("time", [])))):
        rows.append(
            {
                "time": daily.get("time", [])[index],
                "weather_code": daily.get("weather_code", [])[index],
                "temperature_2m_max": daily.get("temperature_2m_max", [])[index],
                "temperature_2m_min": daily.get("temperature_2m_min", [])[index],
                "precipitation_probability_max": daily.get("precipitation_probability_max", [])[index],
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Get current weather and a smart forecast for any city")
    parser.add_argument("--city", default="London", help="City name to search")
    parser.add_argument("--days", type=int, default=5, help="Number of forecast days to display")
    args = parser.parse_args()

    try:
        location = geocode_city(args.city)
        weather_data = get_weather_forecast(location["latitude"], location["longitude"], days=max(1, min(args.days, 7)))
        print_report(location, weather_data, max(1, min(args.days, 7)))
        return 0
    except (error.URLError, ValueError, KeyError, TypeError) as exc:
        print(f"Weather lookup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
