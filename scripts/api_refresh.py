from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from spatial_config import LAT_MAX, LAT_MIN, LON_MAX, LON_MIN
from weather_db import import_weather_history_csv

DATA_DIR = BASE_DIR / "data"
JSON_DIR = DATA_DIR / "json"
WEATHER_HISTORY_CSV = DATA_DIR / "weather_history.csv"
WEATHER_HISTORY_EDA_CSV = DATA_DIR / "weather_history_for_eda.csv"

METEOSTAT_HOST = "meteostat.p.rapidapi.com"
METEOSTAT_BASE_URL = f"https://{METEOSTAT_HOST}"
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"
DEFAULT_STATION_IDS = ("12625", "12650", "11934")
STATION_NAME_MAP = {"12625": "Zakopane", "12650": "Kasprowy Wierch", "11934": "Poprad_Tatry"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Odswiezanie danych pogodowych dla projektu tatry-weather."
    )
    parser.add_argument(
        "--mode",
        choices=("history", "current", "forecast", "all"),
        default="all",
        help="Zakres odswiezania danych.",
    )
    parser.add_argument(
        "--history-start",
        default="2020-01-01",
        help="Data poczatkowa dla danych historycznych (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--history-end",
        default="2025-01-01",
        help="Data koncowa dla danych historycznych (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--grid-size",
        type=int,
        default=10,
        help="Liczba punktow siatki w osi lat/lon dla OpenWeather.",
    )
    parser.add_argument(
        "--import-to-db",
        action="store_true",
        help="Po zapisie weather_history.csv zaimportuj dane do SQLite.",
    )
    return parser.parse_args()


def load_required_env() -> tuple[str, str]:
    load_dotenv()

    rapidapi_key = os.getenv("RAPIDAPI_KEY")
    openweather_key = os.getenv("OPENWEATHERAPI_KEY")

    missing = []
    if not rapidapi_key:
        missing.append("RAPIDAPI_KEY")
    if not openweather_key:
        missing.append("OPENWEATHERAPI_KEY")

    if missing:
        missing_values = ", ".join(missing)
        raise RuntimeError(f"Brakuje zmiennych srodowiskowych: {missing_values}")

    return rapidapi_key, openweather_key


def get_latitudes_and_longitudes(grid_size: int) -> tuple[np.ndarray, np.ndarray]:
    latitudes = np.linspace(LAT_MIN, LAT_MAX, grid_size)
    longitudes = np.linspace(LON_MIN, LON_MAX, grid_size)
    return latitudes, longitudes


def get_meteostat_headers(rapidapi_key: str) -> dict[str, str]:
    return {
        "x-rapidapi-key": rapidapi_key,
        "x-rapidapi-host": METEOSTAT_HOST,
        "Content-Type": "application/json",
    }


def fetch_json(url: str, *, params: dict, headers: dict | None = None) -> dict:
    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def refresh_history(
    rapidapi_key: str,
    *,
    start_date: str,
    end_date: str,
    station_ids: tuple[str, ...] = DEFAULT_STATION_IDS,
) -> Path:
    dfs: list[pd.DataFrame] = []
    headers = get_meteostat_headers(rapidapi_key)

    for station_id in station_ids:
        data = fetch_json(
            f"{METEOSTAT_BASE_URL}/stations/daily",
            params={"station": station_id, "start": start_date, "end": end_date},
            headers=headers,
        )["data"]
        df = pd.DataFrame(data)
        df["station_id"] = station_id
        dfs.append(df)

    df_api_data = pd.concat(dfs, axis=0).reset_index(drop=True)
    df_api_data["station_id"] = df_api_data["station_id"].replace(STATION_NAME_MAP)

    columns_dict_rename = {
        "tavg": "avg_temp",
        "tmin": "min_temp",
        "tmax": "max_temp",
        "prcp": "precipitation_total_mm",
        "snow": "max_snow_dept_mm",
        "wdir": "wind_direction",
        "wspd": "avg_wind_speed_km/h",
        "wpgt": "max_wind_speed",
        "pres": "pressure",
        "tsun": "sunshine_total_min",
        "station_id": "station_name",
    }
    df_api_data = df_api_data.rename(columns_dict_rename, axis=1)
    df_api_data.to_csv(WEATHER_HISTORY_EDA_CSV, index=False)
    return WEATHER_HISTORY_EDA_CSV


def get_current_weather(lat: float, lon: float, openweather_key: str) -> dict:
    return fetch_json(
        f"{OPENWEATHER_BASE_URL}/weather",
        params={"lat": lat, "lon": lon, "appid": openweather_key, "units": "metric"},
    )["main"]


def get_air_pollution(lat: float, lon: float, openweather_key: str) -> float | None:
    data = fetch_json(
        f"{OPENWEATHER_BASE_URL}/air_pollution/forecast",
        params={"lat": lat, "lon": lon, "appid": openweather_key},
    )["list"]
    if not data:
        return None
    return data[0]["components"]["pm10"]


def refresh_current(openweather_key: str, *, grid_size: int) -> Path:
    latitudes, longitudes = get_latitudes_and_longitudes(grid_size)
    dfs: list[pd.DataFrame] = []
    batch_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for lat in tqdm(latitudes, desc="Latitudes"):
        for lon in longitudes:
            data = get_current_weather(float(lat), float(lon), openweather_key)
            df = pd.DataFrame(data, index=[0])
            df["pm10"] = get_air_pollution(float(lat), float(lon), openweather_key)
            df["lat"] = float(lat)
            df["lon"] = float(lon)
            df["download_timestamp"] = batch_timestamp
            dfs.append(df)

    df_api_openweather = pd.concat(dfs, ignore_index=True)
    df_api_openweather = df_api_openweather.drop(
        ["temp_min", "temp_max", "sea_level", "grnd_level"],
        axis=1,
        errors="ignore",
    ).reset_index(drop=True)

    if WEATHER_HISTORY_CSV.exists():
        existing_df = pd.read_csv(WEATHER_HISTORY_CSV)
        df_api_openweather = pd.concat([existing_df, df_api_openweather], ignore_index=True)
        df_api_openweather = df_api_openweather.drop_duplicates(
            subset=["lat", "lon", "download_timestamp"], keep="last"
        )

    df_api_openweather = df_api_openweather.sort_values(
        by=["download_timestamp", "lat", "lon"]
    ).reset_index(drop=True)
    df_api_openweather.to_csv(WEATHER_HISTORY_CSV, index=False)
    return WEATHER_HISTORY_CSV


def get_forecast(lat: float, lon: float, openweather_key: str) -> dict:
    response_json = fetch_json(
        f"{OPENWEATHER_BASE_URL}/forecast",
        params={"lat": lat, "lon": lon, "appid": openweather_key, "units": "metric"},
    )
    temps = [item["main"]["temp"] for item in response_json["list"]]
    timestamps = [item["dt_txt"] for item in response_json["list"]]

    return {
        "lat": lat,
        "lon": lon,
        "temperatures": dict(zip(timestamps, temps)),
    }


def refresh_forecast(openweather_key: str, *, grid_size: int) -> Path:
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    latitudes, longitudes = get_latitudes_and_longitudes(grid_size)
    json_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    forecast_data = []

    for lat in tqdm(latitudes, desc="Latitudes"):
        for lon in longitudes:
            forecast_data.append(
                get_forecast(float(lat), float(lon), openweather_key)
            )

    output_path = JSON_DIR / json_filename
    output_path.write_text(json.dumps(forecast_data, indent=2), encoding="utf-8")
    return output_path


def main() -> None:
    args = parse_args()
    rapidapi_key, openweather_key = load_required_env()

    if args.mode in ("history", "all"):
        history_path = refresh_history(
            rapidapi_key,
            start_date=args.history_start,
            end_date=args.history_end,
        )
        print(f"Saved historical data to {history_path}")

    if args.mode in ("current", "all"):
        current_path = refresh_current(openweather_key, grid_size=args.grid_size)
        print(f"Saved current weather data to {current_path}")

        if args.import_to_db:
            inserted_count, skipped_count = import_weather_history_csv(current_path)
            print(
                f"SQLite import finished. Inserted: {inserted_count}, "
                f"Skipped duplicates: {skipped_count}"
            )

    if args.mode in ("forecast", "all"):
        forecast_path = refresh_forecast(openweather_key, grid_size=args.grid_size)
        print(f"Saved forecast data to {forecast_path}")


if __name__ == "__main__":
    main()
