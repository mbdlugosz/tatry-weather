from __future__ import annotations

from collections import deque
from pathlib import Path

import altair as alt
import folium
import pandas as pd
import streamlit as st
from branca.element import Element

from ai_risk import assess_tatra_risk, prepare_ai_point_payload
from dashboard_utils import (
    FORECAST_DIR,
    HISTORICAL_LABELS,
    HISTORICAL_STATION_CSV,
    WEATHER_HISTORY_CSV,
    attach_forecast_point_metadata,
    build_forecast_point_catalog,
    build_heatmap,
    dataframe_to_csv_bytes,
    dataframe_to_excel_bytes,
    format_value,
    load_forecast_export_frame,
    load_historical_data,
    load_historical_dates,
    load_latest_forecast,
    load_source_csv,
    render_card_title,
    render_folium_map,
    render_metric,
    render_panel,
    render_risk_note_prose,
    resolve_map_request,
)
from spatial_config import ROUTE_GRAPH, ROUTE_TEMPLATES, TATRA_PLACE_COORDINATES


def find_nearest_catalog_point(point_catalog_df: pd.DataFrame, lat: float, lon: float) -> pd.Series | None:
    if point_catalog_df.empty:
        return None

    distances = (point_catalog_df["lat"] - lat) ** 2 + (point_catalog_df["lon"] - lon) ** 2
    nearest_index = distances.idxmin()
    return point_catalog_df.loc[nearest_index]


def _normalize_sentence(text: str) -> str:
    cleaned = " ".join(str(text).strip().split())
    if not cleaned:
        return ""
    if cleaned[-1] not in ".!?":
        cleaned = f"{cleaned}."
    return cleaned


def build_risk_description(assessment_data: dict, map_request: dict) -> str:
    sentences = [_normalize_sentence(item) for item in assessment_data.get("justification", []) if item]
    if not sentences:
        return "Brak uzasadnienia."

    if map_request["kind"] == "route" and len(map_request["points"]) >= 2:
        start_label = map_request["points"][0]["label"]
        end_label = map_request["points"][-1]["label"]
        intro = f"Ocena dotyczy trasy z {start_label} do {end_label}. "
    else:
        intro = ""

    return intro + " ".join(sentences)


def build_point_temperature_summary(
    forecast_df: pd.DataFrame,
    point_id: str,
    point_label: str,
    reference_time: pd.Timestamp,
) -> dict | None:
    point_df = forecast_df.loc[forecast_df["point_id"] == point_id].sort_values("forecast_time")
    if point_df.empty:
        return None

    current_row = point_df.loc[point_df["forecast_time"] == reference_time]
    if current_row.empty:
        current_temp = float(point_df.iloc[0]["temperature"])
    else:
        current_temp = float(current_row.iloc[0]["temperature"])

    return {
        "Punkt": point_label,
        "Temperatura": current_temp,
    }


def build_point_series(forecast_df: pd.DataFrame, point_id: str, series_label: str) -> pd.DataFrame:
    start_time = pd.Timestamp(forecast_df["forecast_time"].min())
    end_time = start_time + pd.Timedelta(hours=24)
    point_df = (
        forecast_df.loc[forecast_df["point_id"] == point_id, ["forecast_time", "temperature"]]
        .loc[lambda df: (df["forecast_time"] >= start_time) & (df["forecast_time"] <= end_time)]
        .sort_values("forecast_time")
        .copy()
    )
    point_df["series_label"] = series_label
    return point_df


def build_route_samples(route_points: list[dict]) -> list[dict]:
    if len(route_points) < 2:
        return route_points

    start_point = route_points[0]
    end_point = route_points[-1]
    template_key = (start_point["label"], end_point["label"])
    if template_key in ROUTE_TEMPLATES:
        template_names = ROUTE_TEMPLATES[template_key]
        template_points: list[dict] = []
        for place_name in template_names:
            place_payload = TATRA_PLACE_COORDINATES.get(place_name)
            if place_payload is None:
                continue
            template_points.append(
                {
                    "lat": float(place_payload["lat"]),
                    "lon": float(place_payload["lon"]),
                    "label": place_name,
                    "role": "route_segment",
                }
            )
        if len(template_points) >= 2:
            return template_points

    graph_path = find_route_path(start_point["label"], end_point["label"])
    if graph_path:
        graph_points: list[dict] = []
        for place_name in graph_path:
            place_payload = TATRA_PLACE_COORDINATES.get(place_name)
            if place_payload is None:
                continue
            graph_points.append(
                {
                    "lat": float(place_payload["lat"]),
                    "lon": float(place_payload["lon"]),
                    "label": place_name,
                    "role": "route_segment",
                }
            )
        if len(graph_points) >= 2:
            return graph_points

    fractions = [0.0, 0.25, 0.5, 0.75, 1.0]
    samples: list[dict] = []
    used_labels = {start_point["label"], end_point["label"]}

    for sample_index, fraction in enumerate(fractions):
        lat = float(start_point["lat"]) + (float(end_point["lat"]) - float(start_point["lat"])) * fraction
        lon = float(start_point["lon"]) + (float(end_point["lon"]) - float(start_point["lon"])) * fraction
        if sample_index == 0:
            label = start_point["label"]
        elif sample_index == len(fractions) - 1:
            label = end_point["label"]
        else:
            nearest_name = min(
                TATRA_PLACE_COORDINATES,
                key=lambda place_name: (
                    (lat - float(TATRA_PLACE_COORDINATES[place_name]["lat"])) ** 2
                    + (lon - float(TATRA_PLACE_COORDINATES[place_name]["lon"])) ** 2
                ),
            )
            label = nearest_name if nearest_name not in used_labels else f"Trasa {sample_index}"
            used_labels.add(label)
        samples.append(
            {
                "lat": lat,
                "lon": lon,
                "label": label,
                "role": "route_segment",
            }
        )

    return samples


def find_route_path(start_label: str, end_label: str) -> list[str]:
    if start_label == end_label:
        return [start_label]
    if start_label not in ROUTE_GRAPH or end_label not in ROUTE_GRAPH:
        return []

    queue: deque[tuple[str, list[str]]] = deque([(start_label, [start_label])])
    visited = {start_label}

    while queue:
        current_node, path = queue.popleft()
        for neighbor in ROUTE_GRAPH.get(current_node, []):
            if neighbor in visited:
                continue
            next_path = [*path, neighbor]
            if neighbor == end_label:
                return next_path
            visited.add(neighbor)
            queue.append((neighbor, next_path))

    return []


def build_route_label(map_request: dict) -> str:
    if map_request["kind"] == "route" and len(map_request["points"]) >= 2:
        return f"Trasa: {map_request['points'][0]['label']} -> {map_request['points'][-1]['label']}"
    if map_request["kind"] == "point" and map_request["points"]:
        return f"Lokalizacja: {map_request['points'][0]['label']}"
    return "Analizowane punkty"


def render_risk_view() -> None:
    forecast_df, source_path = load_latest_forecast()
    if forecast_df.empty or source_path is None:
        st.warning("Brak prognozy w aktualnym obszarze. Odswiez dane forecast i uruchom dashboard ponownie.")
        return

    forecast_df = attach_forecast_point_metadata(forecast_df)
    point_catalog_df = build_forecast_point_catalog(forecast_df)
    analysis_start_time = forecast_df["forecast_time"].min()
    filtered_df = forecast_df[forecast_df["forecast_time"] == analysis_start_time].copy()

    if "risk_assessment_result" not in st.session_state:
        st.session_state["risk_assessment_result"] = None

    input_col, content_col = st.columns([0.78, 2.82], vertical_alignment="top")

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
                "Mapa pokaze opisana lokalizacje, a ocena ryzyka zostanie dopasowana do danych prognozy dla tego obszaru."
            )

            if st.button("Ocen ryzyko", use_container_width=True):
                if not described_point.strip():
                    st.error("Wpisz opis lokalizacji lub trasy.")
                    st.stop()
                current_map_request = resolve_map_request(described_point)
                if current_map_request["kind"] == "unresolved":
                    st.session_state["risk_assessment_result"] = None
                    st.error("Wpisana lokalizacja nie nalezy do Tatr albo nie zostala rozpoznana.")
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
    chart_points: list[dict] = []
    chart_series_frames: list[pd.DataFrame] = []
    show_assessment = map_request["kind"] != "unresolved"

    with content_col:
        if assessment_data and show_assessment:
            risk_label_map = {
                "safe": "Niskie",
                "risky": "Podwyzszone",
                "dangerous": "Wysokie",
            }
            risk_level = assessment_data["recommendation"]
            risk_label = risk_label_map.get(risk_level, risk_level)
            risk_description = build_risk_description(assessment_data, map_request)
            render_risk_note_prose(risk_level, risk_label, risk_description)
        elif map_request["kind"] == "unresolved" and described_point.strip():
            render_panel(
                "Brak oceny",
                "Wpisana lokalizacja nie nalezy do Tatr albo nie zostala rozpoznana, dlatego dashboard nie pokazuje oceny ryzyka ani wykresu.",
            )
        else:
            render_panel(
                "Instrukcja",
                "Wpisz lokalizacje lub trase i uruchom ocene. Odpowiedz z uzasadnieniem pojawi sie nad mapa, "
                "a obok mapy zobaczysz temperature dla analizowanych punktow widocznych na mapie.",
            )

        map_col, chart_col = st.columns(2, vertical_alignment="top")

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
                    point_summary = build_point_temperature_summary(
                        forecast_df,
                        nearest_point["point_id"],
                        user_point["label"],
                        analysis_start_time,
                    )
                    if point_summary is not None:
                        chart_points.append(point_summary)
                    chart_series_frames.append(
                        build_point_series(
                            forecast_df,
                            nearest_point["point_id"],
                            user_point["label"],
                        )
                    )
            elif map_request["kind"] == "route":
                route_points = map_request["points"]
                route_samples = build_route_samples(route_points)
                route_coordinates = [[point["lat"], point["lon"]] for point in route_samples]
                route_label = f"Trasa: {route_points[0]['label']} -> {route_points[-1]['label']}"
                map_bounds.extend(route_coordinates)
                folium.PolyLine(
                    route_coordinates,
                    color="#2f6fed",
                    weight=5,
                    opacity=0.85,
                    tooltip=route_label,
                ).add_to(forecast_map)
                for point in route_points:
                    marker_color = "green" if point["role"] == "start" else "red"
                    marker_label = "Start" if point["role"] == "start" else "Meta"
                    folium.Marker(
                        location=[point["lat"], point["lon"]],
                        icon=folium.Icon(color=marker_color, icon="flag", prefix="fa"),
                        tooltip=f"{marker_label}: {point['label']}",
                    ).add_to(forecast_map)

                sampled_point_ids: set[str] = set()
                for sample in route_samples:
                    map_bounds.append([sample["lat"], sample["lon"]])
                    folium.CircleMarker(
                        location=[sample["lat"], sample["lon"]],
                        radius=6,
                        color="#2f6fed",
                        weight=1,
                        fill=True,
                        fill_color="#f8fbff",
                        fill_opacity=0.95,
                        tooltip=sample["label"],
                    ).add_to(forecast_map)
                    nearest_point = find_nearest_catalog_point(point_catalog_df, sample["lat"], sample["lon"])
                    if nearest_point is None or nearest_point["point_id"] in sampled_point_ids:
                        continue
                    sampled_point_ids.add(nearest_point["point_id"])
                    point_summary = build_point_temperature_summary(
                        forecast_df,
                        nearest_point["point_id"],
                        sample["label"],
                        analysis_start_time,
                    )
                    if point_summary is not None:
                        chart_points.append(point_summary)
                    chart_series_frames.append(
                        build_point_series(
                            forecast_df,
                            nearest_point["point_id"],
                            sample["label"],
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
                            Wpisana lokalizacja nie nalezy do Tatr albo nie zostala rozpoznana. Uzyj nazwy miejsca z Tatr albo wspolrzednych z obszaru siatki.
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
            st.subheader("Wykres temperatury")
            if not show_assessment:
                render_panel(
                    "Brak wykresu",
                    "Wykres nie jest wyswietlany, poniewaz wpisana lokalizacja nie nalezy do Tatr albo nie zostala rozpoznana.",
                )
            elif not chart_series_frames and assessment_data:
                matched_point_df = point_catalog_df.loc[
                    point_catalog_df["point_id"] == assessment_data["matched_point_id"]
                ]
                if not matched_point_df.empty:
                    matched_point = matched_point_df.iloc[0]
                    point_summary = build_point_temperature_summary(
                        forecast_df,
                        matched_point["point_id"],
                        "Analizowany punkt",
                        analysis_start_time,
                    )
                    if point_summary is not None:
                        chart_points.append(point_summary)
                    chart_series_frames.append(
                        build_point_series(
                            forecast_df,
                            matched_point["point_id"],
                            "Analizowany punkt",
                        )
                    )
            if show_assessment and chart_series_frames:
                chart_df = pd.concat(chart_series_frames, ignore_index=True)
                chart_title = f"Przebieg temperatur w ciagu 24 godzin dla {build_route_label(map_request).lower()}"
                chart = (
                    alt.Chart(chart_df)
                    .mark_line(point=True, strokeWidth=2.4)
                    .encode(
                        x=alt.X("forecast_time:T", title="Godzina", axis=alt.Axis(format="%H:%M", labelAngle=0)),
                        y=alt.Y("temperature:Q", title="Temperatura [°C]"),
                        color=alt.Color("series_label:N", title="Odcinek trasy"),
                        tooltip=[
                            alt.Tooltip("series_label:N", title="Seria"),
                            alt.Tooltip("forecast_time:T", title="Czas", format="%Y-%m-%d %H:%M"),
                            alt.Tooltip("temperature:Q", title="Temperatura", format=".2f"),
                        ],
                    )
                    .properties(height=420, title=chart_title)
                    .configure(
                        background="#fbfcfb",
                        axis=alt.Axis(
                            labelColor="#17313b",
                            titleColor="#17313b",
                            gridColor="#dce6e2",
                            domainColor="#c8d6d1",
                            tickColor="#c8d6d1",
                        ),
                        legend=alt.Legend(
                            titleColor="#17313b",
                            labelColor="#17313b",
                            fillColor="#fbfcfb",
                            strokeColor="#d8e2df",
                        ),
                        title=alt.TitleConfig(color="#17313b", fontSize=16, anchor="start"),
                        view=alt.ViewConfig(fill="#fbfcfb", stroke="#d8e2df"),
                    )
                )
                st.altair_chart(chart, use_container_width=True)
                st.caption(
                    "Wykres pokazuje 24-godzinny przebieg temperatur dla startu, mety i punktow posrednich wyznaczonych na trasie."
                )
            elif show_assessment:
                render_panel(
                    "Brak wykresu",
                    "Po rozpoznaniu lokalizacji lub trasy dashboard pokaze tutaj przebieg temperatur w kolejnych godzinach.",
                )


def render_history_view() -> None:
    historical_df = load_historical_data()
    if historical_df.empty:
        st.warning("Brak danych w weather_history.csv. Odswiez dane i uruchom dashboard ponownie.")
        return

    historical_df = historical_df.dropna(subset=["download_timestamp"]).copy()
    available_dates = load_historical_dates()
    if not available_dates:
        st.warning("Brak poprawnych dat w weather_history.csv.")
        return

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
        return

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


def render_forecast_view() -> None:
    forecast_df, source_path = load_latest_forecast()
    if forecast_df.empty or source_path is None:
        st.warning("Brak prognozy w aktualnym obszarze. Odswiez dane forecast i uruchom dashboard ponownie.")
        return

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


DATASET_OPTIONS = {
    "weather_history": "Weather history (CSV)",
    "eda_history": "Dane historyczne EDA (CSV)",
    "forecast_snapshot": "Prognoza pogody (JSON)",
}


def get_current_forecast_snapshots() -> list[dict]:
    snapshots: list[dict] = []
    for path in sorted(FORECAST_DIR.glob("*.json"), reverse=True):
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


def render_export_view() -> None:
    side_col, content_col = st.columns([0.9, 2.5], vertical_alignment="top", gap="medium")

    with side_col:
        with st.container(border=True):
            render_card_title("Filtry")
            selected_dataset = st.selectbox(
                "Zbior danych",
                options=list(DATASET_OPTIONS),
                format_func=lambda value: DATASET_OPTIONS[value],
            )

            source_df = None
            base_filename = None
            json_bytes = None
            json_filename = None
            export_moment_label = None

            if selected_dataset == "weather_history":
                source_df = load_source_csv(WEATHER_HISTORY_CSV)
                base_filename = "tatry_weather_history"
                if not source_df.empty and "download_timestamp" in source_df.columns:
                    timestamps = pd.to_datetime(
                        source_df["download_timestamp"],
                        format="%Y%m%d_%H%M%S",
                        errors="coerce",
                    ).dropna()
                    if not timestamps.empty:
                        ts_min = timestamps.min().strftime("%Y-%m-%d %H:%M:%S")
                        ts_max = timestamps.max().strftime("%Y-%m-%d %H:%M:%S")
                        export_moment_label = ts_min if ts_min == ts_max else f"{ts_min} -> {ts_max}"
            elif selected_dataset == "eda_history":
                source_df = load_source_csv(HISTORICAL_STATION_CSV)
                base_filename = "tatry_history_eda"
                if not source_df.empty and "date" in source_df.columns:
                    dates = pd.to_datetime(source_df["date"], errors="coerce").dropna()
                    if not dates.empty:
                        date_min = dates.min().strftime("%Y-%m-%d")
                        date_max = dates.max().strftime("%Y-%m-%d")
                        export_moment_label = date_min if date_min == date_max else f"{date_min} -> {date_max}"
            else:
                snapshots = get_current_forecast_snapshots()
                if not snapshots:
                    st.warning("Brak zapisanych snapshotow prognozy.")
                    return
                snapshot_labels = [item["label"] for item in snapshots]
                default_label = snapshot_labels[0]
                previous_label = st.session_state.get("export_snapshot_label")
                select_index = snapshot_labels.index(previous_label) if previous_label in snapshot_labels else 0
                selected_snapshot_label = st.selectbox(
                    "Moment pobrania",
                    options=snapshot_labels,
                    index=select_index,
                    key="export_snapshot_label",
                )
                selected_snapshot = next(item for item in snapshots if item["label"] == selected_snapshot_label)
                selected_snapshot_path = Path(selected_snapshot["path"])
                if not selected_snapshot_path.exists():
                    st.session_state["export_snapshot_label"] = default_label
                    st.rerun()
                source_df = load_forecast_export_frame(selected_snapshot_path)
                base_filename = f"tatry_forecast_{selected_snapshot['timestamp'].strftime('%Y%m%d_%H%M%S')}"
                json_bytes = selected_snapshot_path.read_bytes()
                json_filename = selected_snapshot_path.name
                export_moment_label = selected_snapshot["label"]

    if source_df is None or source_df.empty:
        st.warning("Brak danych do pobrania dla wybranego zestawu.")
        return

    csv_bytes = dataframe_to_csv_bytes(source_df)
    excel_bytes = dataframe_to_excel_bytes(source_df, sheet_name="source_data")

    with side_col:
        with st.container(border=True):
            render_card_title("Statystyki")
            render_metric("Rekordy", str(len(source_df)))
            render_metric("Kolumny", str(len(source_df.columns)))
            render_metric("CSV", format_value(len(csv_bytes) / 1024, "KB"))
            render_metric("Excel", format_value(len(excel_bytes) / 1024, "KB"))
            if export_moment_label is not None:
                render_metric("Moment", export_moment_label)
            if json_bytes is not None:
                render_metric("JSON", format_value(len(json_bytes) / 1024, "KB"))

    with content_col:
        with st.container(border=True):
            render_card_title("Pobieranie")
            render_panel(
                "Wybrany zestaw",
                f"Aktualnie przygotowany do pobrania: {DATASET_OPTIONS[selected_dataset]}.",
            )
            if export_moment_label is not None:
                render_panel(
                    "Zakres pobrania",
                    f"Eksport obejmie dane z momentu lub zakresu: {export_moment_label}.",
                )
            if json_bytes is None:
                download_col1, download_col2 = st.columns(2)
                download_col3 = None
            else:
                download_col1, download_col2, download_col3 = st.columns(3)
            with download_col1:
                st.download_button(
                    "Pobierz CSV",
                    data=csv_bytes,
                    file_name=f"{base_filename}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with download_col2:
                st.download_button(
                    "Pobierz Excel",
                    data=excel_bytes,
                    file_name=f"{base_filename}.xls",
                    mime="application/vnd.ms-excel",
                    use_container_width=True,
                )
            if download_col3 is not None:
                with download_col3:
                    st.download_button(
                        "Pobierz JSON",
                        data=json_bytes,
                        file_name=json_filename,
                        mime="application/json",
                        use_container_width=True,
                    )

        with st.container(border=True):
            render_card_title("Zakres danych")
            render_panel(
                "Kolumny",
                ", ".join(source_df.columns.astype(str).tolist()),
            )
