from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard_utils import (
    HISTORICAL_LABELS,
    build_heatmap,
    configure_page,
    format_value,
    load_historical_data,
    load_historical_dates,
    render_app_header,
    render_card_title,
    render_folium_map,
    render_metric,
    render_panel,
    render_top_nav,
)


configure_page("Dane historyczne")
render_app_header(
    "Widok zapisanych pomiarow z pliku weather_history.csv. "
    "Ta strona korzysta z tej samej siatki wspolrzednych co prognoza."
)
render_top_nav("history")

historical_df = load_historical_data()
if historical_df.empty:
    st.warning("Brak danych w weather_history.csv. Odswiez dane i uruchom dashboard ponownie.")
    st.stop()

historical_df = historical_df.dropna(subset=["download_timestamp"]).copy()
available_dates = load_historical_dates()
if not available_dates:
    st.warning("Brak poprawnych dat w weather_history.csv.")
    st.stop()

side_col, layout_col = st.columns([0.86, 2.74], vertical_alignment="top", gap="medium")
with side_col:
    with st.container(border=True):
        render_card_title("Filtry")
        if len(available_dates) > 1:
            selected_date = st.select_slider(
                "Data",
                options=available_dates,
                value=available_dates[-1],
                format_func=lambda value: value.strftime("%Y-%m-%d"),
            )
        else:
            selected_date = available_dates[0]
            st.caption(f"Data: {selected_date.strftime('%Y-%m-%d')}")
        selected_metric = st.selectbox(
            "Parametr",
            options=["temp", "feels_like", "pressure", "humidity", "pm10"],
            format_func=lambda key: HISTORICAL_LABELS[key],
        )
        date_df = historical_df[historical_df["download_timestamp"].dt.date == selected_date].copy()
        available_timestamps = [
            pd.Timestamp(value) for value in date_df["download_timestamp"].sort_values().unique().tolist()
        ]
        if len(available_timestamps) > 1:
            selected_range = st.select_slider(
                "Zakres czasu",
                options=available_timestamps,
                value=(available_timestamps[0], available_timestamps[-1]),
                format_func=lambda value: value.strftime("%Y-%m-%d %H:%M:%S"),
            )
        else:
            selected_range = (available_timestamps[0], available_timestamps[0])
            st.caption(f"Czas: {available_timestamps[0].strftime('%Y-%m-%d %H:%M:%S')}")

filtered_df = historical_df[historical_df["download_timestamp"].dt.date == selected_date].copy()
filtered_df = filtered_df[
    filtered_df["download_timestamp"].between(selected_range[0], selected_range[1], inclusive="both")
]
filtered_df = filtered_df.dropna(subset=[selected_metric, "lat", "lon"])

if filtered_df.empty:
    st.info("Brak danych dla wybranego filtra.")
    st.stop()

with side_col:
    with st.container(border=True):
        render_card_title("Statystyki")
        render_metric("Minimum", format_value(float(filtered_df[selected_metric].min())))
        render_metric("Maksimum", format_value(float(filtered_df[selected_metric].max())))
        render_metric("Mediana", format_value(float(filtered_df[selected_metric].median())))
        render_metric("Srednia", format_value(float(filtered_df[selected_metric].mean())))
        render_panel(
            "Interpretacja",
            "Ta strona czyta bezposrednio weather_history.csv, dlatego wspolrzedne powinny odpowiadac "
            "dokladnie tej samej siatce co w plikach prognozy.",
        )

with layout_col:
    st.subheader("Mapa")
    historical_map = build_heatmap(
        filtered_df,
        value_column=selected_metric,
        legend_label=HISTORICAL_LABELS[selected_metric],
    )
    render_folium_map(historical_map, height=760)
