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
    "Widok zapisanych pomiarow z pliku weather_history.csv. "
    "Ta strona korzysta z tej samej siatki wspolrzednych co prognoza.",
)

historical_df = load_historical_data()
if historical_df.empty:
    st.warning("Brak danych w weather_history.csv. Odswiez dane i uruchom dashboard ponownie.")
    st.stop()

timestamp_min = historical_df["download_timestamp"].min()
timestamp_max = historical_df["download_timestamp"].max()

with st.sidebar:
    st.header("Filtry")
    selected_metric = st.selectbox(
        "Parametr",
        options=["temp", "feels_like", "pressure", "humidity", "pm10"],
        format_func=lambda key: HISTORICAL_LABELS[key],
    )

filtered_df = historical_df.copy()
filtered_df = filtered_df.dropna(subset=[selected_metric, "lat", "lon"])

col1, col2, col3, col4 = st.columns(4)
with col1:
    render_metric("Liczba punktow", str(len(filtered_df)))
with col2:
    render_metric("Parametr", HISTORICAL_LABELS[selected_metric])
with col3:
    render_metric(
        "Zakres czasu",
        (
            pd.Timestamp(timestamp_min).strftime("%Y-%m-%d %H:%M:%S")
            if timestamp_min == timestamp_max
            else f"{pd.Timestamp(timestamp_min).strftime('%H:%M:%S')} - {pd.Timestamp(timestamp_max).strftime('%H:%M:%S')}"
        ),
    )
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
        "Ta strona czyta bezposrednio weather_history.csv, dlatego wspolrzedne powinny odpowiadac "
        "dokladnie tej samej siatce co w plikach prognozy.",
    )

st.subheader("Tabela rekordow")
preview_columns = ["download_timestamp", "temp", "feels_like", "pressure", "humidity", "pm10", "lat", "lon"]
st.dataframe(filtered_df[preview_columns], use_container_width=True, hide_index=True)
