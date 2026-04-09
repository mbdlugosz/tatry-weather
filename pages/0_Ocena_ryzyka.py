from __future__ import annotations

import folium
import pandas as pd
import streamlit as st
from branca.element import Element

from ai_risk import assess_tatra_risk, prepare_ai_point_payload
from dashboard_utils import (
    attach_forecast_point_metadata,
    build_forecast_point_catalog,
    configure_page,
    load_latest_forecast,
    render_app_header,
    render_card_title,
    render_folium_map,
    render_panel,
    render_risk_note_detailed,
    render_top_nav,
    resolve_map_request,
)


def find_nearest_catalog_point(point_catalog_df: pd.DataFrame, lat: float, lon: float) -> pd.Series | None:
    if point_catalog_df.empty:
        return None

    distances = (point_catalog_df["lat"] - lat) ** 2 + (point_catalog_df["lon"] - lon) ** 2
    nearest_index = distances.idxmin()
    return point_catalog_df.loc[nearest_index]


def build_point_series(forecast_df: pd.DataFrame, point_id: str, series_label: str) -> pd.DataFrame:
    point_df = (
        forecast_df.loc[forecast_df["point_id"] == point_id, ["forecast_time", "temperature"]]
        .sort_values("forecast_time")
        .copy()
    )
    point_df["series_label"] = series_label
    return point_df


configure_page("Ocena ryzyka")
render_app_header(
    "Ocena ryzyka wedrowki na podstawie 24-godzinnej prognozy temperatur. "
    "Opisz lokalizacje albo trase, a dashboard pokaze miejsce na mapie i szczegolowa ocene ryzyka."
)
render_top_nav("risk")

forecast_df, source_path = load_latest_forecast()
if forecast_df.empty or source_path is None:
    st.warning("Brak prognozy w aktualnym obszarze. Odswiez dane forecast i uruchom dashboard ponownie.")
    st.stop()

forecast_df = attach_forecast_point_metadata(forecast_df)
point_catalog_df = build_forecast_point_catalog(forecast_df)
analysis_start_time = forecast_df["forecast_time"].min()
filtered_df = forecast_df[forecast_df["forecast_time"] == analysis_start_time].copy()

if "risk_assessment_result" not in st.session_state:
    st.session_state["risk_assessment_result"] = None

input_col, content_col = st.columns([0.9, 2.7], vertical_alignment="top")

with input_col:
    with st.container(border=True):
        render_card_title("Ocena ryzyka AI")
        described_point = st.text_area(
            "Opisz lokalizacje lub trase",
            placeholder="Np. Morskie Oko albo Zakopane -> Kasprowy Wierch",
            height=120,
        )
        st.caption(
            "Mozesz wpisac pojedyncze miejsce, trase albo wspolrzedne. "
            "Mapa pokaze opisana lokalizacje, a ocena ryzyka zostanie policzona na najblizszym punkcie siatki prognozy."
        )

        if st.button("Ocen ryzyko", use_container_width=True):
            if not described_point.strip():
                st.error("Wpisz opis lokalizacji lub trasy.")
                st.stop()
            payload = prepare_ai_point_payload(
                forecast_df,
                point_catalog_df,
                start_time=analysis_start_time,
            )
            try:
                with st.spinner("Trwa analiza ryzyka dla wybranej lokalizacji..."):
                    assessment = assess_tatra_risk(
                        payload,
                        point_description=described_point,
                    )
                st.session_state["risk_assessment_result"] = assessment.model_dump()
            except Exception as exc:
                st.session_state["risk_assessment_result"] = None
                st.error(f"Nie udalo sie pobrac oceny ryzyka AI: {exc}")

assessment_data = st.session_state.get("risk_assessment_result")
map_request = resolve_map_request(described_point)
chart_series_frames: list[pd.DataFrame] = []

with content_col:
    if assessment_data:
        risk_label_map = {
            "safe": "Niskie",
            "risky": "Podwyzszone",
            "dangerous": "Wysokie",
        }
        risk_level = assessment_data["recommendation"]
        risk_label = risk_label_map.get(risk_level, risk_level)
        justification_items = assessment_data.get("justification") or ["Brak uzasadnienia."]
        intro_text = (
            f"Ocena dla opisu: {described_point.strip()}. "
            f"Model dopasowal najblizszy punkt prognozy i na tej podstawie wyznaczyl poziom ryzyka."
        )
        render_risk_note_detailed(risk_level, risk_label, intro_text, justification_items)
    else:
        render_panel(
            "Instrukcja",
            "Wpisz lokalizacje lub trase i uruchom ocene. Odpowiedz z uzasadnieniem pojawi sie nad mapa, "
            "a obok mapy zobaczysz przebieg temperatur dla analizowanego punktu lub punktow trasy.",
        )

    map_col, chart_col = st.columns([1.7, 1.15], vertical_alignment="top")

    with map_col:
        st.subheader("Mapa lokalizacji")
        center_lat = float(filtered_df["lat"].mean())
        center_lon = float(filtered_df["lon"].mean())
        forecast_map = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=11,
            tiles="CartoDB Positron",
            control_scale=True,
        )
        map_bounds: list[list[float]] = filtered_df[["lat", "lon"]].dropna().values.tolist()

        for row in filtered_df[["lat", "lon", "point_label"]].dropna().itertuples(index=False):
            lat, lon, point_label = float(row[0]), float(row[1]), str(row[2])
            folium.CircleMarker(
                location=[lat, lon],
                radius=4,
                color="#5f6f77",
                weight=1,
                fill=True,
                fill_color="#eef3f1",
                fill_opacity=0.9,
                tooltip=f"Punkt siatki: {point_label}",
            ).add_to(forecast_map)

        if map_request["kind"] == "point":
            user_point = map_request["points"][0]
            nearest_point = find_nearest_catalog_point(point_catalog_df, user_point["lat"], user_point["lon"])
            map_bounds.append([user_point["lat"], user_point["lon"]])
            folium.Marker(
                location=[user_point["lat"], user_point["lon"]],
                icon=folium.Icon(color="blue", icon="map-pin", prefix="fa"),
                tooltip=f"Wpisana lokalizacja: {user_point['label']}",
            ).add_to(forecast_map)
            if nearest_point is not None:
                chart_series_frames.append(
                    build_point_series(
                        forecast_df,
                        nearest_point["point_id"],
                        f"{user_point['label']} | najblizszy punkt siatki",
                    )
                )
        elif map_request["kind"] == "route":
            route_points = map_request["points"]
            route_coordinates = [[point["lat"], point["lon"]] for point in route_points]
            map_bounds.extend(route_coordinates)
            folium.PolyLine(
                route_coordinates,
                color="#2f6fed",
                weight=5,
                opacity=0.85,
                tooltip=f"Trasa: {route_points[0]['label']} -> {route_points[1]['label']}",
            ).add_to(forecast_map)
            for point in route_points:
                marker_color = "green" if point["role"] == "start" else "red"
                marker_label = "Start" if point["role"] == "start" else "Meta"
                folium.Marker(
                    location=[point["lat"], point["lon"]],
                    icon=folium.Icon(color=marker_color, icon="flag", prefix="fa"),
                    tooltip=f"{marker_label}: {point['label']}",
                ).add_to(forecast_map)
                nearest_point = find_nearest_catalog_point(point_catalog_df, point["lat"], point["lon"])
                if nearest_point is not None:
                    chart_series_frames.append(
                        build_point_series(
                            forecast_df,
                            nearest_point["point_id"],
                            f"{marker_label}: {point['label']}",
                        )
                    )

        if map_request["kind"] == "unresolved":
            forecast_map.get_root().html.add_child(
                Element(
                    """
                    <div style="
                        position: fixed;
                        top: 22px;
                        right: 22px;
                        z-index: 9999;
                        background: rgba(255, 248, 231, 0.96);
                        color: #6c4b16;
                        padding: 10px 12px;
                        border-radius: 12px;
                        border: 1px solid #e7c98a;
                        box-shadow: 0 10px 24px rgba(0,0,0,0.10);
                        font-size: 13px;
                        max-width: 280px;
                    ">
                        Nie rozpoznano dokladnej lokalizacji lub trasy. Uzyj nazwy miejsca z Tatr albo wspolrzednych, np. 49.2322, 19.9817.
                    </div>
                    """
                )
            )

        if map_bounds:
            lats = [float(point[0]) for point in map_bounds]
            lons = [float(point[1]) for point in map_bounds]
            forecast_map.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])

        render_folium_map(forecast_map, height=760)

    with chart_col:
        st.subheader("Przebieg temperatur")
        if not chart_series_frames and assessment_data:
            matched_point_df = point_catalog_df.loc[
                point_catalog_df["point_id"] == assessment_data["matched_point_id"]
            ]
            if not matched_point_df.empty:
                matched_point = matched_point_df.iloc[0]
                chart_series_frames.append(
                    build_point_series(
                        forecast_df,
                        matched_point["point_id"],
                        "Analizowany punkt siatki",
                    )
                )

        if chart_series_frames:
            chart_df = pd.concat(chart_series_frames, ignore_index=True)
            chart_frame = (
                chart_df.pivot(index="forecast_time", columns="series_label", values="temperature")
                .sort_index()
            )
            st.line_chart(chart_frame, height=420)
            st.caption(
                "Wykres pokazuje przebieg temperatur dla punktu siatki najblizszego wpisanej lokalizacji "
                "albo dla punktow najblizszych startowi i mecie trasy."
            )
        else:
            render_panel(
                "Brak wykresu",
                "Po rozpoznaniu lokalizacji lub trasy dashboard pokaze tutaj serie temperatur dla analizowanych punktow.",
            )
