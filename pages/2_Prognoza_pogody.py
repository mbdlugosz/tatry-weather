from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard_utils import (
    attach_forecast_point_metadata,
    build_heatmap,
    configure_page,
    format_value,
    load_latest_forecast,
    render_app_header,
    render_card_title,
    render_folium_map,
    render_metric,
    render_panel,
    render_top_nav,
)


configure_page("Prognoza pogody")
render_app_header(
    "Widok prognozy temperatur zapisanej w plikach JSON. "
    "Wybierz termin prognozy, aby porownac przestrzenny rozklad temperatur w obszarze Tatr."
)
render_top_nav("forecast")

forecast_df, source_path = load_latest_forecast()
if forecast_df.empty or source_path is None:
    st.warning("Brak prognozy w aktualnym obszarze. Odswiez dane forecast i uruchom dashboard ponownie.")
    st.stop()

forecast_df = attach_forecast_point_metadata(forecast_df)

side_col, layout_col = st.columns([0.78, 2.62], vertical_alignment="top")
with side_col:
    with st.container(border=True):
        render_card_title("Filtry")
        available_times = forecast_df["forecast_time"].sort_values().unique().tolist()
        if len(available_times) > 1:
            selected_time = st.select_slider(
                "Termin prognozy",
                options=available_times,
                format_func=lambda value: pd.Timestamp(value).strftime("%Y-%m-%d %H:%M"),
            )
        else:
            selected_time = available_times[0]
            st.caption(f"Termin prognozy: {pd.Timestamp(selected_time).strftime('%Y-%m-%d %H:%M')}")

filtered_df = forecast_df[forecast_df["forecast_time"] == selected_time].copy()

with side_col:
    with st.container(border=True):
        render_card_title("Statystyki")
        render_metric("Pobrano", pd.to_datetime(source_path.stem, format="%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S"))
        render_metric("Termin", pd.Timestamp(selected_time).strftime("%Y-%m-%d %H:%M"))
        render_metric("Minimum", format_value(float(filtered_df["temperature"].min()), "C"))
        render_metric("Maksimum", format_value(float(filtered_df["temperature"].max()), "C"))
        render_metric("Mediana", format_value(float(filtered_df["temperature"].median()), "C"))
        render_metric("Srednia", format_value(float(filtered_df["temperature"].mean()), "C"))
        render_panel(
            "Interpretacja",
            "Warstwa prognozy pochodzi z najnowszego pliku JSON. Po kolejnym odswiezeniu danych dashboard automatycznie "
            "zacznie pracowac na nowym zestawie prognoz.",
        )

with layout_col:
    st.subheader("Mapa")
    forecast_map = build_heatmap(
        filtered_df,
        value_column="temperature",
        legend_label="Temperatura prognozowana",
    )
    render_folium_map(forecast_map, height=760)
