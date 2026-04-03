from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from folium import Element
from folium.plugins import HeatMap

from spatial_config import LAT_MAX, LAT_MIN, LON_MAX, LON_MIN, STATION_COORDINATES, is_inside_bounds


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "database" / "weather.db"
FORECAST_DIR = BASE_DIR / "data" / "json"
WEATHER_HISTORY_CSV = BASE_DIR / "data" / "weather_history.csv"
HISTORICAL_STATION_CSV = BASE_DIR / "data" / "weather_history_for_eda.csv"

HISTORICAL_LABELS = {
    "avg_temp": "Srednia temperatura",
    "min_temp": "Minimalna temperatura",
    "max_temp": "Maksymalna temperatura",
    "pressure": "Cisnienie",
    "avg_wind_speed_km/h": "Srednia predkosc wiatru",
    "max_wind_speed": "Maksymalna predkosc wiatru",
    "temp": "Temperatura",
    "feels_like": "Temperatura odczuwalna",
    "humidity": "Wilgotnosc",
    "pm10": "PM10",
}


def configure_page(title: str) -> None:
    st.set_page_config(page_title=title, layout="wide")
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(180deg, #f7f4ed 0%, #f1f5f3 100%);
            color: #17313b;
        }
        [data-testid="stSidebar"] {
            background: #ecf2f1;
            border-right: 1px solid #d8e1de;
        }
        .block-container {
            max-width: 1380px;
            padding-top: 1.3rem;
            padding-bottom: 2rem;
        }
        h1, h2, h3, p, div, span, label {
            color: #17313b;
        }
        .hero-card {
            background: linear-gradient(135deg, #dde8e5, #eef3f1);
            border: 1px solid #ced9d6;
            border-radius: 22px;
            padding: 1.35rem 1.5rem;
            box-shadow: 0 10px 28px rgba(21, 43, 51, 0.08);
            margin-bottom: 1rem;
        }
        .panel-card {
            background: #fbfcfb;
            border: 1px solid #d8e2df;
            border-radius: 18px;
            padding: 1rem 1.1rem;
            box-shadow: 0 8px 24px rgba(21, 43, 51, 0.06);
        }
        .metric-card {
            background: #fbfcfb;
            border: 1px solid #d8e2df;
            border-radius: 18px;
            padding: 1rem 1.1rem;
            min-height: 118px;
            box-shadow: 0 8px 20px rgba(21, 43, 51, 0.05);
        }
        .metric-label {
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #627982;
        }
        .metric-value {
            font-size: 1.75rem;
            font-weight: 700;
            color: #17313b;
            margin-top: 0.45rem;
            line-height: 1.15;
        }
        .body-copy {
            color: #42616b;
            line-height: 1.7;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_historical_data(db_path: Path = DATABASE_PATH) -> pd.DataFrame:
    if not WEATHER_HISTORY_CSV.exists():
        return pd.DataFrame()

    df = pd.read_csv(WEATHER_HISTORY_CSV)
    if df.empty:
        return df

    df["download_timestamp"] = pd.to_datetime(
        df["download_timestamp"], format="%Y%m%d_%H%M%S", errors="coerce"
    )
    mask = df.apply(lambda row: is_inside_bounds(float(row["lat"]), float(row["lon"])), axis=1)
    return df.loc[mask].reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_station_history(csv_path: Path = HISTORICAL_STATION_CSV) -> pd.DataFrame:
    if not csv_path.exists():
        return pd.DataFrame()

    df = pd.read_csv(csv_path)
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["lat"] = df["station_name"].map(lambda name: STATION_COORDINATES.get(name, {}).get("lat"))
    df["lon"] = df["station_name"].map(lambda name: STATION_COORDINATES.get(name, {}).get("lon"))
    return df.dropna(subset=["date", "lat", "lon"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_latest_forecast(forecast_dir: Path = FORECAST_DIR) -> tuple[pd.DataFrame, Path | None]:
    forecast_files = sorted(forecast_dir.glob("*.json"))
    if not forecast_files:
        return pd.DataFrame(), None

    latest_file = max(forecast_files, key=lambda path: path.stat().st_mtime)
    raw_data = json.loads(latest_file.read_text(encoding="utf-8"))

    rows: list[dict] = []
    for item in raw_data:
        lat = float(item["lat"])
        lon = float(item["lon"])
        if not is_inside_bounds(lat, lon):
            continue
        for forecast_time, temp in item["temperatures"].items():
            rows.append(
                {
                    "lat": lat,
                    "lon": lon,
                    "forecast_time": pd.to_datetime(forecast_time),
                    "temperature": float(temp),
                }
            )

    return pd.DataFrame(rows), latest_file


def render_hero(title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="hero-card">
            <div style="font-size:2rem; font-weight:800; color:#17313b;">{title}</div>
            <div class="body-copy" style="margin-top:0.55rem; max-width:820px;">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_panel(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="panel-card">
            <div style="font-size:1.05rem; font-weight:700; margin-bottom:0.45rem;">{title}</div>
            <div class="body-copy">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_bounds(df: pd.DataFrame) -> tuple[list[float], list[list[float]]]:
    if df.empty:
        center = [(LAT_MIN + LAT_MAX) / 2, (LON_MIN + LON_MAX) / 2]
        return center, [[LAT_MIN, LON_MIN], [LAT_MAX, LON_MAX]]

    lat_min = float(df["lat"].min())
    lat_max = float(df["lat"].max())
    lon_min = float(df["lon"].min())
    lon_max = float(df["lon"].max())

    lat_pad = max((lat_max - lat_min) * 0.08, 0.006)
    lon_pad = max((lon_max - lon_min) * 0.08, 0.006)
    center = [(lat_min + lat_max) / 2, (lon_min + lon_max) / 2]
    bounds = [
        [lat_min - lat_pad, lon_min - lon_pad],
        [lat_max + lat_pad, lon_max + lon_pad],
    ]
    return center, bounds


def get_value_range(df: pd.DataFrame, value_column: str) -> tuple[float, float]:
    vmin = float(df[value_column].min())
    vmax = float(df[value_column].max())
    if vmin == vmax:
        vmax = vmin + 1.0
    return vmin, vmax


def value_to_color(value: float, *, vmin: float, vmax: float) -> str:
    palette = ["#28536b", "#2a9d8f", "#e9c46a", "#f4a261", "#d1495b"]
    ratio = (value - vmin) / (vmax - vmin)
    ratio = min(max(ratio, 0.0), 1.0)
    index = min(int(ratio * (len(palette) - 1)), len(palette) - 1)
    return palette[index]


def build_heatmap(
    df: pd.DataFrame,
    *,
    value_column: str,
    legend_label: str,
    radius: int = 24,
) -> folium.Map:
    center, bounds = get_bounds(df)
    vmin, vmax = get_value_range(df, value_column)
    weather_map = folium.Map(
        location=center,
        zoom_start=12,
        tiles="CartoDB Positron",
        control_scale=True,
    )

    HeatMap(
        data=df[["lat", "lon", value_column]].dropna().values.tolist(),
        radius=radius,
        blur=18,
        min_opacity=0.28,
        max_zoom=13,
        gradient={
            0.1: "#28536b",
            0.35: "#2a9d8f",
            0.6: "#e9c46a",
            0.8: "#f4a261",
            1.0: "#d1495b",
        },
    ).add_to(weather_map)

    for row in df[["lat", "lon", value_column]].dropna().itertuples(index=False):
        lat, lon, value = float(row[0]), float(row[1]), float(row[2])
        folium.CircleMarker(
            location=[lat, lon],
            radius=7,
            color="#17313b",
            weight=1.1,
            fill=True,
            fill_color=value_to_color(value, vmin=vmin, vmax=vmax),
            fill_opacity=0.95,
            tooltip=f"lat: {lat:.6f}<br>lon: {lon:.6f}<br>{legend_label}: {value:.2f}",
        ).add_to(weather_map)

    folium.Rectangle(
        bounds=bounds,
        color="#4f6770",
        weight=1,
        fill=True,
        fill_opacity=0.03,
        opacity=0.45,
    ).add_to(weather_map)
    weather_map.fit_bounds(bounds)

    legend_html = f"""
    <div style="
        position: fixed;
        bottom: 22px;
        left: 22px;
        z-index: 9999;
        background: rgba(251,252,251,0.95);
        padding: 10px 12px;
        border-radius: 12px;
        border: 1px solid rgba(23,49,59,0.12);
        box-shadow: 0 10px 24px rgba(0,0,0,0.10);
        font-size: 13px;
        color: #17313b;
        min-width: 240px;
    ">
        <strong>{legend_label}</strong><br>
        <div style="margin-top:6px; margin-bottom:8px;">Heatmapa pokazuje rozklad przestrzenny, a markery zachowuja dokladne polozenie punktow siatki.</div>
        <div style="height:10px; border-radius:999px; background: linear-gradient(90deg, #28536b 0%, #2a9d8f 25%, #e9c46a 50%, #f4a261 75%, #d1495b 100%);"></div>
        <div style="display:flex; justify-content:space-between; margin-top:6px;">
            <span>{vmin:.2f}</span>
            <span>{vmax:.2f}</span>
        </div>
    </div>
    """
    weather_map.get_root().html.add_child(Element(legend_html))
    return weather_map


def build_station_map(
    df: pd.DataFrame,
    *,
    value_column: str,
    legend_label: str,
) -> folium.Map:
    center, bounds = get_bounds(df)
    vmin, vmax = get_value_range(df, value_column)
    station_map = folium.Map(
        location=center,
        zoom_start=10,
        tiles="CartoDB Positron",
        control_scale=True,
    )

    HeatMap(
        data=df[["lat", "lon", value_column]].dropna().values.tolist(),
        radius=35,
        blur=28,
        min_opacity=0.18,
        max_zoom=11,
        gradient={
            0.1: "#28536b",
            0.35: "#2a9d8f",
            0.6: "#e9c46a",
            0.8: "#f4a261",
            1.0: "#d1495b",
        },
    ).add_to(station_map)

    for row in df[["station_name", "lat", "lon", value_column]].dropna().itertuples(index=False):
        station_name, lat, lon, value = row
        folium.CircleMarker(
            location=[float(lat), float(lon)],
            radius=10,
            color="#17313b",
            weight=1.4,
            fill=True,
            fill_color=value_to_color(float(value), vmin=vmin, vmax=vmax),
            fill_opacity=0.98,
            tooltip=(
                f"stacja: {station_name}<br>"
                f"lat: {float(lat):.4f}<br>"
                f"lon: {float(lon):.4f}<br>"
                f"{legend_label}: {float(value):.2f}"
            ),
        ).add_to(station_map)
        folium.Marker(
            location=[float(lat), float(lon)],
            icon=folium.DivIcon(
                html=(
                    "<div style='font-size:12px;font-weight:700;color:#17313b;"
                    "background:rgba(251,252,251,0.88);padding:2px 6px;border-radius:8px;"
                    "border:1px solid #d8e2df;white-space:nowrap;'>"
                    f"{station_name}</div>"
                )
            ),
        ).add_to(station_map)

    station_map.fit_bounds(bounds)
    return station_map


def render_folium_map(map_object: folium.Map, *, height: int = 640) -> None:
    st.components.v1.html(map_object._repr_html_(), height=height)


def format_value(value: float, unit: str = "") -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "brak"
    suffix = f" {unit}" if unit else ""
    return f"{value:.2f}{suffix}"
