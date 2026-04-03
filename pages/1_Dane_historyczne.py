from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard_utils import (
    HISTORICAL_LABELS,
    build_heatmap,
    configure_page,
    format_value,
    load_historical_data,
    render_folium_map,
    render_hero,
    render_metric,
    render_panel,
)


configure_page("Dane historyczne")

render_hero(
    "Dane historyczne",
    "Widok pomiarow zapisanych w bazie SQLite. Wybierz paczke czasowa i parametr, "
    "aby przeanalizowac rozklad warunkow pogodowych oraz poziomu PM10 na siatce punktow.",
)

historical_df = load_historical_data()
if historical_df.empty:
    st.warning("Brak danych historycznych w aktualnym obszarze. Odswiez dane i zaimportuj je do SQLite.")
    st.stop()

available_timestamps = (
    historical_df["download_timestamp"].dropna().sort_values(ascending=False).unique().tolist()
)

with st.sidebar:
    st.header("Filtry")
    selected_timestamp = st.selectbox(
        "Paczka pomiarowa",
        available_timestamps,
        format_func=lambda value: pd.Timestamp(value).strftime("%Y-%m-%d %H:%M:%S"),
    )
    selected_metric = st.selectbox(
        "Parametr",
        options=list(HISTORICAL_LABELS),
        format_func=lambda key: HISTORICAL_LABELS[key],
    )

filtered_df = historical_df[historical_df["download_timestamp"] == selected_timestamp].copy()
filtered_df = filtered_df.dropna(subset=[selected_metric, "lat", "lon"])

col1, col2, col3, col4 = st.columns(4)
with col1:
    render_metric("Liczba punktow", str(len(filtered_df)))
with col2:
    render_metric("Parametr", HISTORICAL_LABELS[selected_metric])
with col3:
    render_metric("Znacznik czasu", pd.Timestamp(selected_timestamp).strftime("%Y-%m-%d %H:%M:%S"))
with col4:
    render_metric("Srednia", format_value(float(filtered_df[selected_metric].mean())))

if filtered_df.empty:
    st.info("Brak danych dla wybranego filtra.")
    st.stop()

map_col, info_col = st.columns([1.85, 1])
with map_col:
    st.subheader("Mapa")
    historical_map = build_heatmap(
        filtered_df,
        value_column=selected_metric,
        legend_label=HISTORICAL_LABELS[selected_metric],
    )
    render_folium_map(historical_map)
with info_col:
    st.subheader("Statystyki")
    render_metric("Minimum", format_value(float(filtered_df[selected_metric].min())))
    render_metric("Maksimum", format_value(float(filtered_df[selected_metric].max())))
    render_metric("Mediana", format_value(float(filtered_df[selected_metric].median())))
    render_panel(
        "Interpretacja",
        "Markery pokazują dokładne położenie punktów siatki. Heatmapa ułatwia szybkie odczytanie obszarów "
        "o wyższych i niższych wartościach wybranego parametru.",
    )

st.subheader("Tabela rekordow")
preview_columns = ["download_timestamp", "temp", "feels_like", "pressure", "humidity", "pm10", "lat", "lon"]
st.dataframe(filtered_df[preview_columns], use_container_width=True, hide_index=True)
