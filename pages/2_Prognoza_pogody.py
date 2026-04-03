from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard_utils import (
    build_heatmap,
    configure_page,
    format_value,
    load_latest_forecast,
    render_folium_map,
    render_hero,
    render_metric,
    render_panel,
)


configure_page("Prognoza pogody")

render_hero(
    "Prognoza pogody",
    "Widok najnowszej prognozy temperatur zapisanej w pliku JSON. "
    "Wybierz termin prognozy, aby porownac przestrzenny rozklad temperatur w obszarze Tatr.",
)

forecast_df, source_path = load_latest_forecast()
if forecast_df.empty or source_path is None:
    st.warning("Brak prognozy w aktualnym obszarze. Odswiez dane forecast i uruchom dashboard ponownie.")
    st.stop()

available_times = forecast_df["forecast_time"].sort_values().unique().tolist()

with st.sidebar:
    st.header("Filtry")
    selected_time = st.select_slider(
        "Termin prognozy",
        options=available_times,
        format_func=lambda value: pd.Timestamp(value).strftime("%Y-%m-%d %H:%M"),
    )

filtered_df = forecast_df[forecast_df["forecast_time"] == selected_time].copy()

col1, col2, col3, col4 = st.columns(4)
with col1:
    render_metric("Liczba punktow", str(len(filtered_df)))
with col2:
    render_metric("Termin", pd.Timestamp(selected_time).strftime("%Y-%m-%d %H:%M"))
with col3:
    render_metric("Plik prognozy", source_path.name)
with col4:
    render_metric("Srednia temperatura", format_value(float(filtered_df["temperature"].mean()), "C"))

map_col, info_col = st.columns([1.85, 1])
with map_col:
    st.subheader("Mapa")
    forecast_map = build_heatmap(
        filtered_df,
        value_column="temperature",
        legend_label="Temperatura prognozowana",
    )
    render_folium_map(forecast_map)
with info_col:
    st.subheader("Statystyki")
    render_metric("Minimum", format_value(float(filtered_df["temperature"].min()), "C"))
    render_metric("Maksimum", format_value(float(filtered_df["temperature"].max()), "C"))
    render_metric("Mediana", format_value(float(filtered_df["temperature"].median()), "C"))
    render_panel(
        "Interpretacja",
        "Warstwa prognozy pochodzi z najnowszego pliku JSON. Po kolejnym odswiezeniu danych dashboard automatycznie "
        "zacznie pracowac na nowym zestawie prognoz.",
    )

st.subheader("Tabela prognozy")
st.dataframe(
    filtered_df.rename(columns={"forecast_time": "czas_prognozy", "temperature": "temperatura"}),
    use_container_width=True,
    hide_index=True,
)
