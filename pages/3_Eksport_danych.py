from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from dashboard_utils import (
    HISTORICAL_STATION_CSV,
    FORECAST_DIR,
    WEATHER_HISTORY_CSV,
    configure_page,
    dataframe_to_csv_bytes,
    dataframe_to_excel_bytes,
    format_value,
    load_forecast_export_frame,
    load_source_csv,
    render_app_header,
    render_card_title,
    render_metric,
    render_panel,
    render_top_nav,
)


configure_page("Eksport danych")
render_app_header(
    "Pobierz dane zrodlowe projektu w formacie CSV lub Excel. "
    "Mozesz wybrac zapisany plik weather history albo konkretny snapshot prognozy."
)
render_top_nav("export")

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
                st.stop()
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
    st.stop()

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
