from __future__ import annotations

import folium
import pandas as pd
import streamlit as st

from ai_risk import assess_tatra_risk, prepare_ai_point_payload
from dashboard_utils import (
    attach_forecast_point_metadata,
    build_forecast_point_catalog,
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


configure_page("Ocena ryzyka")
render_app_header(
    "Ocena ryzyka wedrowki na podstawie 24-godzinnej prognozy temperatur. "
    "Opisz lokalizacje, a AI dopasuje najbardziej prawdopodobny punkt siatki i oceni ryzyko."
)
render_top_nav("risk")

forecast_df, source_path = load_latest_forecast()
if forecast_df.empty or source_path is None:
    st.warning("Brak prognozy w aktualnym obszarze. Odswiez dane forecast i uruchom dashboard ponownie.")
    st.stop()

forecast_df = attach_forecast_point_metadata(forecast_df)
point_catalog_df = build_forecast_point_catalog(forecast_df)

side_col, layout_col = st.columns([0.85, 2.55], vertical_alignment="top")
with side_col:
    with st.container(border=True):
        render_card_title("Filtry")
        available_times = forecast_df["forecast_time"].sort_values().unique().tolist()
        if len(available_times) > 1:
            selected_time = st.select_slider(
                "Start prognozy",
                options=available_times,
                format_func=lambda value: pd.Timestamp(value).strftime("%Y-%m-%d %H:%M"),
            )
        else:
            selected_time = available_times[0]
            st.caption(f"Start prognozy: {pd.Timestamp(selected_time).strftime('%Y-%m-%d %H:%M')}")

filtered_df = forecast_df[forecast_df["forecast_time"] == selected_time].copy()

if "risk_assessment_result" not in st.session_state:
    st.session_state["risk_assessment_result"] = None

with side_col:
    with st.container(border=True):
        render_card_title("Ocena ryzyka AI")
        described_point = st.text_area(
            "Opisz lokalizacje",
            placeholder="Np. okolice Kasprowego, bardziej na wschod od centrum obszaru",
            height=120,
        )
        st.caption(
            "Model dostaje dane dla wszystkich punktow siatki i na podstawie opisu wybiera "
            "najbardziej prawdopodobny punkt przed ocena ryzyka."
        )

        if st.button("Ocen ryzyko", use_container_width=True):
            if not described_point.strip():
                st.error("Wpisz opis lokalizacji.")
                st.stop()
            payload = prepare_ai_point_payload(
                forecast_df,
                point_catalog_df,
                start_time=selected_time,
            )
            try:
                with st.spinner("Trwa analiza ryzyka dla wybranego punktu..."):
                    assessment = assess_tatra_risk(
                        payload,
                        point_description=described_point,
                    )
                st.session_state["risk_assessment_result"] = assessment.model_dump()
            except Exception as exc:
                st.session_state["risk_assessment_result"] = None
                st.error(f"Nie udalo sie pobrac oceny ryzyka AI: {exc}")

assessment_data = st.session_state.get("risk_assessment_result")
highlighted_point_df = pd.DataFrame()

with side_col:
    with st.container(border=True):
        render_card_title("Wynik")
        render_metric("Pobrano", pd.to_datetime(source_path.stem, format="%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S"))
        render_metric("Start", pd.Timestamp(selected_time).strftime("%Y-%m-%d %H:%M"))
        if assessment_data:
            matched_point = point_catalog_df.loc[
                point_catalog_df["point_id"] == assessment_data["matched_point_id"]
            ]
            if matched_point.empty:
                matched_point_label = assessment_data["matched_point_label"]
                matched_point_description = "Brak dodatkowego opisu punktu."
            else:
                highlighted_point_df = filtered_df.merge(
                    matched_point[["point_id", "lat", "lon"]],
                    on=["point_id", "lat", "lon"],
                    how="inner",
                )
                matched_point_label = matched_point["point_display"].iloc[0]
                matched_point_description = matched_point["point_description"].iloc[0]

            risk_label_map = {
                "safe": "Niskie",
                "risky": "Podwyzszone",
                "dangerous": "Wysokie",
            }
            render_metric(
                "Ocena ryzyka",
                risk_label_map.get(assessment_data["recommendation"], assessment_data["recommendation"]),
            )
            st.markdown(f"**Dopasowany punkt:** {matched_point_label}")
            st.write(f"**Opis punktu:** {matched_point_description}")
            st.write(f"**Dlaczego ten punkt:** {assessment_data['match_reason']}")
            short_justification = assessment_data["justification"][0] if assessment_data["justification"] else "Brak uzasadnienia."
            st.write(f"**Krotkie uzasadnienie:** {short_justification}")
            if len(assessment_data["justification"]) > 1:
                st.write("**Dodatkowe powody:**")
                for item in assessment_data["justification"][1:]:
                    st.write(f"- {item}")
        else:
            render_metric("Ocena ryzyka", "Brak")
            render_panel(
                "Instrukcja",
                "Wpisz opis lokalizacji i uruchom ocene. AI przeanalizuje wszystkie punkty siatki, "
                "dopasuje najbardziej prawdopodobny i zaznaczy go na mapie.",
            )

with layout_col:
    st.subheader("Mapa punktow dla wybranego startu prognozy")
    forecast_map = build_heatmap(
        filtered_df,
        value_column="temperature",
        legend_label="Temperatura prognozowana",
    )
    if not highlighted_point_df.empty:
        point_row = highlighted_point_df.iloc[0]
        folium.CircleMarker(
            location=[float(point_row["lat"]), float(point_row["lon"])],
            radius=12,
            color="#9f1d35",
            weight=3,
            fill=True,
            fill_color="#f7d154",
            fill_opacity=0.95,
            tooltip=(
                f"Wybrany punkt AI: {point_row['point_label']}<br>"
                f"Temperatura prognozowana: {float(point_row['temperature']):.2f}"
            ),
        ).add_to(forecast_map)
        folium.Marker(
            location=[float(point_row["lat"]), float(point_row["lon"])],
            icon=folium.DivIcon(
                html=(
                    "<div style='font-size:12px;font-weight:700;color:#9f1d35;"
                    "background:rgba(255,248,220,0.95);padding:2px 6px;border-radius:8px;"
                    "border:2px solid #9f1d35;white-space:nowrap;'>Punkt AI</div>"
                )
            ),
        ).add_to(forecast_map)
    render_folium_map(forecast_map, height=760)
