from __future__ import annotations

import json
import math
import re
import sqlite3
import unicodedata
from base64 import b64encode
from difflib import get_close_matches
from difflib import SequenceMatcher
from html import escape
from io import BytesIO
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from folium import Element
from folium.plugins import HeatMap

from spatial_config import (
    LAT_MAX,
    LAT_MIN,
    LON_MAX,
    LON_MIN,
    STATION_COORDINATES,
    TATRA_PLACE_COORDINATES,
    is_inside_bounds,
)


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "database" / "weather.db"
FORECAST_DIR = BASE_DIR / "data" / "json"
WEATHER_HISTORY_CSV = BASE_DIR / "data" / "weather_history.csv"
HISTORICAL_STATION_CSV = BASE_DIR / "data" / "weather_history_for_eda.csv"
APP_HEADER_IMAGE = BASE_DIR / "grafika.png"

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


def get_file_signature(path: Path) -> tuple[bool, int, int]:
    if not path.exists():
        return False, 0, 0
    stat = path.stat()
    return True, stat.st_mtime_ns, stat.st_size


def _get_header_image_data_uri() -> str | None:
    if not APP_HEADER_IMAGE.exists():
        return None
    encoded = b64encode(APP_HEADER_IMAGE.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def configure_page(title: str) -> None:
    st.set_page_config(page_title=title, layout="wide", initial_sidebar_state="collapsed")
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(180deg, #f7f4ed 0%, #f1f5f3 100%);
            color: #17313b;
        }
        [data-testid="stHeader"] {
            background: transparent !important;
        }
        [data-testid="stSidebarNav"] {
            display: none;
        }
        [data-testid="stSidebarCollapsedControl"] {
            display: none;
        }
        button[aria-label="Open sidebar"],
        button[title="Open sidebar"],
        button[aria-label="Close sidebar"],
        button[title="Close sidebar"] {
            display: none !important;
        }
        .block-container {
            max-width: 100%;
            padding-top: 1.3rem;
            padding-left: 1.4rem;
            padding-right: 1.4rem;
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
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #fcfdfb;
        }
        .metric-card {
            background: #fbfcfb;
            border: 1px solid #d8e2df;
            border-radius: 18px;
            padding: 0.8rem 0.9rem;
            min-height: 96px;
            box-shadow: 0 8px 20px rgba(21, 43, 51, 0.05);
        }
        .metric-label {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #627982;
        }
        .metric-value {
            font-size: 1.35rem;
            font-weight: 700;
            color: #17313b;
            margin-top: 0.35rem;
            line-height: 1.15;
        }
        .body-copy {
            color: #42616b;
            line-height: 1.6;
            font-size: 0.94rem;
        }
        .top-nav-label {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #627982;
            margin-bottom: 0.55rem;
        }
        .filter-card {
            background: #fbfcfb;
            border: 1px solid #d8e2df;
            border-radius: 18px;
            padding: 0.9rem 1rem 1rem;
            box-shadow: 0 8px 24px rgba(21, 43, 51, 0.06);
            margin-bottom: 1rem;
        }
        .card-title {
            font-size: 0.98rem;
            font-weight: 700;
            color: #17313b;
            margin-bottom: 0.7rem;
        }
        .app-header {
            display: flex;
            align-items: center;
            gap: 1.15rem;
            margin-bottom: 0.95rem;
        }
        .app-header-image {
            width: 164px;
            max-width: 100%;
            height: auto;
            display: block;
            flex: 0 0 auto;
        }
        .app-header-copy {
            min-width: 0;
        }
        .app-title {
            font-size: 1.9rem;
            font-weight: 800;
            color: #17313b;
            line-height: 1.1;
            margin-bottom: 0.35rem;
        }
        .app-subtitle {
            color: #5a7178;
            font-size: 0.98rem;
            line-height: 1.5;
            margin-bottom: 0.95rem;
            max-width: 900px;
        }
        @media (max-width: 768px) {
            .app-header {
                align-items: flex-start;
                gap: 0.9rem;
            }
            .app-header-image {
                width: 120px;
            }
        }
        div[data-baseweb="select"] > div {
            background: #fffef9 !important;
            border-color: #c7d5d1 !important;
            min-height: 42px !important;
        }
        div[data-baseweb="select"] input,
        div[data-baseweb="select"] div {
            color: #17313b !important;
            font-size: 0.9rem !important;
        }
        div[data-baseweb="popover"],
        div[data-baseweb="popover"] * {
            color: #17313b !important;
        }
        div[data-baseweb="popover"] {
            background: transparent !important;
            box-shadow: none !important;
            min-width: unset !important;
        }
        div[data-baseweb="menu"] {
            background: #fffef9 !important;
            min-width: unset !important;
        }
        div[data-baseweb="menu"] ul,
        div[data-baseweb="menu"] li {
            background: #fffef9 !important;
            color: #17313b !important;
            font-size: 0.9rem !important;
        }
        div[data-baseweb="select"] + div {
            background: #fffef9 !important;
        }
        [role="listbox"] {
            background: #fffef9 !important;
            border: 1px solid #d8e2df !important;
            box-shadow: 0 10px 24px rgba(21, 43, 51, 0.08) !important;
            min-width: unset !important;
            width: 100% !important;
        }
        [role="option"] {
            background: #fffef9 !important;
            color: #17313b !important;
        }
        [role="option"][aria-selected="true"] {
            background: #eef4f1 !important;
            color: #17313b !important;
        }
        [data-baseweb="popover"] [role="presentation"] {
            background: transparent !important;
        }
        [data-testid="stWidgetLabel"] label,
        [data-testid="stWidgetLabel"] p {
            font-size: 0.84rem !important;
            color: #516870 !important;
        }
        div[data-testid="stDownloadButton"] > button {
            background: #fffef9 !important;
            color: #17313b !important;
            border: 1px solid #d8e2df !important;
            box-shadow: 0 8px 18px rgba(21, 43, 51, 0.05) !important;
        }
        div[data-testid="stDownloadButton"] > button:hover {
            background: #f7faf8 !important;
            border-color: #c6d5d1 !important;
            color: #17313b !important;
        }
        button[data-testid="StyledFullScreenButton"],
        button[title="View fullscreen"],
        details[data-testid="stActionMenu"] summary,
        [data-testid="stElementToolbar"] button {
            background: #fbfcfb !important;
            color: #17313b !important;
            border: 1px solid #d8e2df !important;
            border-radius: 10px !important;
            box-shadow: 0 6px 16px rgba(21, 43, 51, 0.06) !important;
        }
        details[data-testid="stActionMenu"] div[role="menu"],
        [data-testid="stElementToolbar"] [role="menu"] {
            background: #fbfcfb !important;
            border: 1px solid #d8e2df !important;
            box-shadow: 0 10px 24px rgba(21, 43, 51, 0.08) !important;
        }
        details[data-testid="stActionMenu"] div[role="menu"] *,
        [data-testid="stElementToolbar"] [role="menu"] * {
            color: #17313b !important;
        }
        div[data-testid="stTextArea"] textarea {
            background: #fffdf7 !important;
            color: #17313b !important;
            border: 1px solid #d7e2de !important;
            border-radius: 14px !important;
        }
        div[data-testid="stTextArea"] textarea::placeholder {
            color: #7a8f96 !important;
        }
        div[data-testid="stTextArea"] textarea:focus {
            border-color: #bdd0ca !important;
            box-shadow: 0 0 0 1px #bdd0ca !important;
        }
        div[data-testid="stButton"] > button {
            background: #f7f3e8 !important;
            color: #17313b !important;
            border: 1px solid #d9d2be !important;
            box-shadow: 0 8px 18px rgba(21, 43, 51, 0.06) !important;
        }
        div[data-testid="stButton"] > button:hover {
            background: #f1eadb !important;
            border-color: #cfc4aa !important;
            color: #17313b !important;
        }
        .risk-note {
            border-radius: 18px;
            padding: 1rem 1.05rem;
            border: 1px solid transparent;
            box-shadow: 0 10px 24px rgba(21, 43, 51, 0.07);
        }
        .risk-note-level {
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            font-weight: 700;
            margin-bottom: 0.45rem;
        }
        .risk-note-title {
            font-size: 1.18rem;
            font-weight: 800;
            margin-bottom: 0.45rem;
        }
        .risk-note-body {
            font-size: 0.95rem;
            line-height: 1.55;
            color: #26414a;
        }
        .risk-note-list {
            margin: 0.7rem 0 0;
            padding-left: 1.15rem;
            color: #26414a;
        }
        .risk-note-list li {
            margin-bottom: 0.38rem;
            line-height: 1.5;
        }
        .risk-note-paragraph {
            margin-top: 0.7rem;
            color: #26414a;
            line-height: 1.65;
            font-size: 0.96rem;
        }
        .risk-note-safe {
            background: #edf8f0;
            border-color: #b9ddc2;
        }
        .risk-note-safe .risk-note-level,
        .risk-note-safe .risk-note-title {
            color: #1f6a36;
        }
        .risk-note-risky {
            background: #fff4df;
            border-color: #ebd19a;
        }
        .risk-note-risky .risk-note-level,
        .risk-note-risky .risk-note-title {
            color: #9a6110;
        }
        .risk-note-dangerous {
            background: #fdecec;
            border-color: #efb2b2;
        }
        .risk-note-dangerous .risk-note-level,
        .risk-note-dangerous .risk-note-title {
            color: #a33131;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def _load_historical_data_cached(csv_path: Path, _signature: tuple[bool, int, int]) -> pd.DataFrame:
    if not csv_path.exists():
        return pd.DataFrame()

    df = pd.read_csv(csv_path)
    if df.empty:
        return df

    df["download_timestamp"] = pd.to_datetime(
        df["download_timestamp"], format="%Y%m%d_%H%M%S", errors="coerce"
    )
    mask = df.apply(lambda row: is_inside_bounds(float(row["lat"]), float(row["lon"])), axis=1)
    return df.loc[mask].reset_index(drop=True)


def load_historical_data(db_path: Path = DATABASE_PATH) -> pd.DataFrame:
    del db_path
    return _load_historical_data_cached(WEATHER_HISTORY_CSV, get_file_signature(WEATHER_HISTORY_CSV))


@st.cache_data(show_spinner=False)
def _load_historical_dates_cached(csv_path: Path, _signature: tuple[bool, int, int]) -> list:
    if not csv_path.exists():
        return []

    df = pd.read_csv(csv_path, usecols=["download_timestamp"])
    if df.empty:
        return []

    timestamps = pd.to_datetime(df["download_timestamp"], format="%Y%m%d_%H%M%S", errors="coerce").dropna()
    return sorted(timestamps.dt.date.unique().tolist())


def load_historical_dates(csv_path: Path = WEATHER_HISTORY_CSV) -> list:
    return _load_historical_dates_cached(csv_path, get_file_signature(csv_path))


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


def load_latest_forecast(forecast_dir: Path = FORECAST_DIR) -> tuple[pd.DataFrame, Path | None]:
    forecast_files = sorted(forecast_dir.glob("*.json"))
    if not forecast_files:
        return pd.DataFrame(), None

    latest_file = max(forecast_files, key=lambda path: path.stat().st_mtime)
    return load_forecast_from_file(latest_file)


@st.cache_data(show_spinner=False)
def _load_forecast_snapshots_cached(forecast_dir: Path, _dir_signature: tuple[tuple[str, int, int], ...]) -> list[dict]:
    forecast_files = sorted(forecast_dir.glob("*.json"))
    snapshots: list[dict] = []

    for path in forecast_files:
        try:
            snapshot_time = pd.to_datetime(path.stem, format="%Y%m%d_%H%M%S", errors="raise")
        except (TypeError, ValueError):
            continue
        snapshots.append(
            {
                "path": path,
                "timestamp": snapshot_time,
                "label": snapshot_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    snapshots.sort(key=lambda item: item["timestamp"], reverse=True)
    return snapshots


def load_forecast_snapshots(forecast_dir: Path = FORECAST_DIR) -> list[dict]:
    dir_signature = tuple(
        (path.name, path.stat().st_mtime_ns, path.stat().st_size)
        for path in sorted(forecast_dir.glob("*.json"))
    )
    return _load_forecast_snapshots_cached(forecast_dir, dir_signature)


@st.cache_data(show_spinner=False)
def _load_forecast_from_file_cached(
    forecast_file: Path,
    _signature: tuple[bool, int, int],
) -> tuple[pd.DataFrame, Path | None]:
    raw_data = json.loads(forecast_file.read_text(encoding="utf-8"))

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

    return pd.DataFrame(rows), forecast_file


def load_forecast_from_file(forecast_file: Path) -> tuple[pd.DataFrame, Path | None]:
    if not forecast_file.exists():
        return pd.DataFrame(), None
    return _load_forecast_from_file_cached(forecast_file, get_file_signature(forecast_file))


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


def render_app_header(description: str) -> None:
    image_markup = ""
    image_data_uri = _get_header_image_data_uri()
    if image_data_uri:
        image_markup = f'<img src="{image_data_uri}" alt="Grafika dashboardu Tatry" class="app-header-image" />'

    st.markdown(
        f"""
        <div class="app-header">
            {image_markup}
            <div class="app-header-copy">
                <div class="app-title">Dashboard pogodowy Tatry</div>
                <div class="app-subtitle">{description}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_top_nav(active_page: str) -> None:
    st.markdown('<div class="top-nav-label">Nawigacja</div>', unsafe_allow_html=True)
    risk_col, history_col, forecast_col, export_col = st.columns(4)

    with risk_col:
        st.page_link(
            "pages/0_Ocena_ryzyka.py",
            label="Ocena ryzyka",
            icon=":material/warning:",
            disabled=active_page == "risk",
            use_container_width=True,
        )

    with history_col:
        st.page_link(
            "pages/1_Dane_historyczne.py",
            label="Dane historyczne",
            icon=":material/stacked_line_chart:",
            disabled=active_page == "history",
            use_container_width=True,
        )
    with forecast_col:
        st.page_link(
            "pages/2_Prognoza_pogody.py",
            label="Prognoza pogody",
            icon=":material/cloud:",
            disabled=active_page == "forecast",
            use_container_width=True,
        )
    with export_col:
        st.page_link(
            "pages/3_Eksport_danych.py",
            label="Eksport danych",
            icon=":material/download:",
            disabled=active_page == "export",
            use_container_width=True,
        )


def render_card_title(title: str) -> None:
    st.markdown(f'<div class="card-title">{title}</div>', unsafe_allow_html=True)


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


def render_risk_note(risk_level: str, title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="risk-note risk-note-{escape(risk_level)}">
            <div class="risk-note-level">Ocena ryzyka</div>
            <div class="risk-note-title">{escape(title)}</div>
            <div class="risk-note-body">{escape(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_risk_note_detailed(risk_level: str, title: str, intro: str, details: list[str]) -> None:
    details_html = "".join(f"<li>{escape(item)}</li>" for item in details if item)
    st.markdown(
        f"""
        <div class="risk-note risk-note-{escape(risk_level)}">
            <div class="risk-note-level">Ocena ryzyka</div>
            <div class="risk-note-title">{escape(title)}</div>
            <div class="risk-note-body">{escape(intro)}</div>
            <ul class="risk-note-list">{details_html}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_risk_note_prose(risk_level: str, title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="risk-note risk-note-{escape(risk_level)}">
            <div class="risk-note-level">Ocena ryzyka</div>
            <div class="risk-note-title">{escape(title)}</div>
            <div class="risk-note-paragraph">{escape(body)}</div>
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


def _get_band_label(ratio: float, *, low_label: str, middle_label: str, high_label: str) -> str:
    if ratio <= 1 / 3:
        return low_label
    if ratio >= 2 / 3:
        return high_label
    return middle_label


def _normalize_location_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_value.lower()).strip()


def _extract_coordinate_pair(text: str) -> dict | None:
    match = re.search(r"(-?\d{1,2}\.\d+)\s*[,;]\s*(-?\d{1,2}\.\d+)", text)
    if not match:
        return None

    lat = float(match.group(1))
    lon = float(match.group(2))
    if not is_inside_bounds(lat, lon):
        return None

    return {
        "label": f"{lat:.4f}, {lon:.4f}",
        "lat": lat,
        "lon": lon,
        "source": "coordinates",
    }


def _resolve_named_place(text: str) -> dict | None:
    normalized_text = _normalize_location_text(text)
    if not normalized_text:
        return None

    alias_lookup: dict[str, tuple[str, dict]] = {}
    best_match: tuple[int, str, dict] | None = None
    for place_name, payload in TATRA_PLACE_COORDINATES.items():
        aliases = payload.get("aliases", [])
        for alias in aliases:
            normalized_alias = _normalize_location_text(alias)
            if normalized_alias:
                alias_lookup[normalized_alias] = (place_name, payload)
            if normalized_alias == normalized_text:
                return {
                    "label": place_name,
                    "lat": float(payload["lat"]),
                    "lon": float(payload["lon"]),
                    "source": "place_catalog",
                }
            if normalized_alias and normalized_alias in normalized_text:
                score = len(normalized_alias)
                if best_match is None or score > best_match[0]:
                    best_match = (
                        score,
                        place_name,
                        {
                            "label": place_name,
                            "lat": float(payload["lat"]),
                            "lon": float(payload["lon"]),
                            "source": "place_catalog",
                        },
                    )

    fuzzy_match = get_close_matches(normalized_text, list(alias_lookup.keys()), n=1, cutoff=0.74)
    if fuzzy_match:
        place_name, payload = alias_lookup[fuzzy_match[0]]
        return {
            "label": place_name,
            "lat": float(payload["lat"]),
            "lon": float(payload["lon"]),
            "source": "place_catalog",
        }

    return None if best_match is None else best_match[2]


def _extract_place_mentions(query: str) -> list[dict]:
    normalized_query = _normalize_location_text(query)
    if not normalized_query:
        return []

    tokens = [token for token in re.split(r"[^a-z0-9]+", normalized_query) if token]
    if not tokens:
        return []

    alias_lookup: dict[str, dict] = {}
    for place_name, payload in TATRA_PLACE_COORDINATES.items():
        for alias in payload.get("aliases", []):
            normalized_alias = _normalize_location_text(alias)
            if normalized_alias:
                alias_lookup[normalized_alias] = {
                    "label": place_name,
                    "lat": float(payload["lat"]),
                    "lon": float(payload["lon"]),
                    "source": "place_catalog",
                }

    matches: list[tuple[int, int, dict]] = []

    for alias, payload in alias_lookup.items():
        alias_tokens = alias.split()
        alias_length = len(alias_tokens)
        if alias in normalized_query:
            position = normalized_query.find(alias)
            matches.append((position, alias_length, payload))

    max_ngram = min(5, len(tokens))
    for size in range(max_ngram, 0, -1):
        for start_index in range(len(tokens) - size + 1):
            candidate = " ".join(tokens[start_index : start_index + size])
            if candidate in alias_lookup:
                continue
            close_match = get_close_matches(candidate, list(alias_lookup.keys()), n=1, cutoff=0.72)
            if not close_match:
                continue
            alias = close_match[0]
            similarity = SequenceMatcher(None, candidate, alias).ratio()
            if similarity < 0.72:
                continue
            matches.append((start_index, size, alias_lookup[alias]))

    ordered_matches: list[dict] = []
    seen_labels: set[str] = set()
    for _, _, payload in sorted(matches, key=lambda item: (item[0], -item[1])):
        label = payload["label"]
        if label in seen_labels:
            continue
        seen_labels.add(label)
        ordered_matches.append(payload)

    return ordered_matches


def _resolve_location_fragment(text: str) -> dict | None:
    return _extract_coordinate_pair(text) or _resolve_named_place(text)


def resolve_map_request(query: str) -> dict:
    stripped_query = query.strip()
    if not stripped_query:
        return {"kind": "none", "points": []}

    route_patterns = [
        r"^\s*(.+?)\s*->\s*(.+?)\s*$",
        r"^\s*(.+?)\s*[-–]\s*(.+?)\s*$",
        r"^\s*trasa\s+z\s+(.+?)\s+do\s+(.+?)\s*$",
        r"^\s*(?:z|od)\s+(.+?)\s+do\s+(.+?)\s*$",
    ]
    for pattern in route_patterns:
        match = re.match(pattern, stripped_query, flags=re.IGNORECASE)
        if not match:
            continue
        start_label = match.group(1).strip()
        end_label = match.group(2).strip()
        start_point = _resolve_location_fragment(start_label)
        end_point = _resolve_location_fragment(end_label)
        if start_point and end_point:
            return {
                "kind": "route",
                "points": [
                    {**start_point, "role": "start", "input_label": start_label},
                    {**end_point, "role": "end", "input_label": end_label},
                ],
            }
        continue

    mentioned_places = _extract_place_mentions(stripped_query)
    if len(mentioned_places) >= 2:
        start_point = mentioned_places[0]
        end_point = mentioned_places[-1]
        return {
            "kind": "route",
            "points": [
                {**start_point, "role": "start", "input_label": start_point["label"]},
                {**end_point, "role": "end", "input_label": end_point["label"]},
            ],
        }
    if len(mentioned_places) == 1:
        return {
            "kind": "point",
            "points": [{**mentioned_places[0], "role": "point", "input_label": mentioned_places[0]["label"]}],
        }

    single_point = _resolve_location_fragment(stripped_query)
    if single_point:
        return {"kind": "point", "points": [{**single_point, "role": "point", "input_label": stripped_query}]}

    return {"kind": "unresolved", "points": []}


def _get_nearest_station_name(lat: float, lon: float) -> str:
    return min(
        STATION_COORDINATES,
        key=lambda station_name: (
            (lat - STATION_COORDINATES[station_name]["lat"]) ** 2
            + (lon - STATION_COORDINATES[station_name]["lon"]) ** 2
        ),
    )


def build_forecast_point_catalog(forecast_df: pd.DataFrame) -> pd.DataFrame:
    if forecast_df.empty:
        return pd.DataFrame(
            columns=[
                "point_id",
                "point_label",
                "point_display",
                "point_description",
                "lat",
                "lon",
                "row_index",
                "col_index",
            ]
        )

    points_df = (
        forecast_df[["lat", "lon"]]
        .drop_duplicates()
        .sort_values(["lat", "lon"], ascending=[False, True])
        .reset_index(drop=True)
    )
    latitudes = sorted(points_df["lat"].unique(), reverse=True)
    longitudes = sorted(points_df["lon"].unique())
    lat_lookup = {value: index for index, value in enumerate(latitudes)}
    lon_lookup = {value: index for index, value in enumerate(longitudes)}

    rows: list[dict] = []
    total_points = len(points_df)
    for point_number, row in enumerate(points_df.itertuples(index=False), start=1):
        lat = float(row.lat)
        lon = float(row.lon)
        lat_ratio = 0.5 if LAT_MAX == LAT_MIN else (lat - LAT_MIN) / (LAT_MAX - LAT_MIN)
        lon_ratio = 0.5 if LON_MAX == LON_MIN else (lon - LON_MIN) / (LON_MAX - LON_MIN)
        vertical = _get_band_label(
            lat_ratio,
            low_label="poludniowa",
            middle_label="centralna",
            high_label="polnocna",
        )
        horizontal = _get_band_label(
            lon_ratio,
            low_label="zachodnia",
            middle_label="centralna",
            high_label="wschodnia",
        )
        if vertical == "centralna" and horizontal == "centralna":
            area_label = "centralna czesc obszaru"
        elif vertical == "centralna":
            area_label = f"{horizontal} czesc obszaru"
        elif horizontal == "centralna":
            area_label = f"{vertical} czesc obszaru"
        else:
            area_label = f"{vertical[:-1]}o-{horizontal} czesc obszaru"

        nearest_station = _get_nearest_station_name(lat, lon)
        point_id = f"P{point_number:03d}"
        point_label = f"{point_id} ({lat:.4f}, {lon:.4f})"
        point_description = (
            f"{area_label}, najblizej punktu odniesienia {nearest_station}, "
            f"wiersz {lat_lookup[lat] + 1} z {len(latitudes)}, kolumna {lon_lookup[lon] + 1} z {len(longitudes)}"
        )
        point_display = (
            f"{point_id} | {area_label} | najblizej: {nearest_station} | "
            f"lat {lat:.4f}, lon {lon:.4f}"
        )
        rows.append(
            {
                "point_id": point_id,
                "point_label": point_label,
                "point_display": point_display,
                "point_description": point_description,
                "lat": lat,
                "lon": lon,
                "row_index": lat_lookup[lat] + 1,
                "col_index": lon_lookup[lon] + 1,
                "total_points": total_points,
            }
        )

    return pd.DataFrame(rows)


def attach_forecast_point_metadata(forecast_df: pd.DataFrame) -> pd.DataFrame:
    if forecast_df.empty:
        return forecast_df.copy()

    point_catalog = build_forecast_point_catalog(forecast_df)
    return forecast_df.merge(point_catalog, on=["lat", "lon"], how="left")


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

    marker_columns = ["lat", "lon", value_column]
    has_point_label = "point_label" in df.columns
    if has_point_label:
        marker_columns.append("point_label")

    for row in df[marker_columns].dropna().itertuples(index=False):
        lat, lon, value = float(row[0]), float(row[1]), float(row[2])
        point_label = row[3] if has_point_label else None
        tooltip_prefix = f"{point_label}<br>" if point_label else ""
        folium.CircleMarker(
            location=[lat, lon],
            radius=7,
            color="#17313b",
            weight=1.1,
            fill=True,
            fill_color=value_to_color(value, vmin=vmin, vmax=vmax),
            fill_opacity=0.95,
            tooltip=f"{tooltip_prefix}lat: {lat:.6f}<br>lon: {lon:.6f}<br>{legend_label}: {value:.2f}",
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
    st.components.v1.html(map_object.get_root().render(), height=height, scrolling=False)


def format_value(value: float, unit: str = "") -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "brak"
    suffix = f" {unit}" if unit else ""
    return f"{value:.2f}{suffix}"


@st.cache_data(show_spinner=False)
def _load_source_csv_cached(csv_path: Path, _signature: tuple[bool, int, int]) -> pd.DataFrame:
    if not csv_path.exists():
        return pd.DataFrame()
    return pd.read_csv(csv_path)


def load_source_csv(csv_path: Path) -> pd.DataFrame:
    return _load_source_csv_cached(csv_path, get_file_signature(csv_path))


@st.cache_data(show_spinner=False)
def _load_forecast_export_frame_cached(forecast_file: Path, _signature: tuple[bool, int, int]) -> pd.DataFrame:
    raw_data = json.loads(forecast_file.read_text(encoding="utf-8"))
    snapshot_time = pd.to_datetime(forecast_file.stem, format="%Y%m%d_%H%M%S", errors="coerce")

    rows: list[dict] = []
    for item in raw_data:
        lat = float(item["lat"])
        lon = float(item["lon"])
        for forecast_time, temp in item["temperatures"].items():
            rows.append(
                {
                    "snapshot_time": snapshot_time,
                    "forecast_time": pd.to_datetime(forecast_time),
                    "lat": lat,
                    "lon": lon,
                    "temperature": float(temp),
                }
            )

    return pd.DataFrame(rows)


def load_forecast_export_frame(forecast_file: Path) -> pd.DataFrame:
    if not forecast_file.exists():
        return pd.DataFrame()
    return _load_forecast_export_frame_cached(forecast_file, get_file_signature(forecast_file))


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    export_df = df.copy()
    for column in export_df.select_dtypes(include=["datetimetz", "datetime64[ns]"]).columns:
        export_df[column] = export_df[column].astype(str)
    return export_df.to_csv(index=False).encode("utf-8")


def dataframe_to_excel_bytes(df: pd.DataFrame, *, sheet_name: str = "data") -> bytes:
    export_df = df.copy()
    for column in export_df.columns:
        if pd.api.types.is_datetime64_any_dtype(export_df[column]):
            export_df[column] = export_df[column].astype(str)

    safe_sheet_name = escape(sheet_name[:31])
    header_cells = "".join(
        f'<Cell ss:StyleID="header"><Data ss:Type="String">{escape(str(column))}</Data></Cell>'
        for column in export_df.columns
    )

    body_rows: list[str] = []
    for row in export_df.itertuples(index=False, name=None):
        cells: list[str] = []
        for value in row:
            if pd.isna(value):
                cell_value = ""
                cell_type = "String"
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                cell_value = str(value)
                cell_type = "Number"
            else:
                cell_value = escape(str(value))
                cell_type = "String"
            cells.append(f'<Cell><Data ss:Type="{cell_type}">{cell_value}</Data></Cell>')
        body_rows.append(f"<Row>{''.join(cells)}</Row>")

    workbook_xml = f"""<?xml version="1.0"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:x="urn:schemas-microsoft-com:office:excel"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
 <Styles>
  <Style ss:ID="header">
   <Font ss:Bold="1"/>
  </Style>
 </Styles>
 <Worksheet ss:Name="{safe_sheet_name}">
  <Table>
   <Row>{header_cells}</Row>
   {''.join(body_rows)}
  </Table>
 </Worksheet>
</Workbook>
"""
    return workbook_xml.encode("utf-8")
