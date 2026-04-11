from __future__ import annotations

import streamlit as st

from dashboard_utils import configure_page, render_app_header, render_top_nav
from dashboard_views import (
    render_export_view,
    render_forecast_view,
    render_history_view,
    render_risk_view,
)


VIEW_CONFIG = {
    "risk": {
        "description": (
            "Ocena ryzyka wedrowki na podstawie 24-godzinnej prognozy temperatur. "
            "Opisz lokalizacje albo trase, a dashboard pokaze miejsce na mapie i szczegolowa ocene ryzyka."
        ),
        "render": render_risk_view,
    },
    "history": {
        "description": (
            "Widok zapisanych pomiarow z pliku weather_history.csv. "
            "Ta strona korzysta z tej samej siatki wspolrzednych co prognoza."
        ),
        "render": render_history_view,
    },
    "forecast": {
        "description": (
            "Widok prognozy temperatur zapisanej w plikach JSON. "
            "Wybierz termin prognozy, aby porownac przestrzenny rozklad temperatur w obszarze Tatr."
        ),
        "render": render_forecast_view,
    },
    "export": {
        "description": (
            "Pobierz dane zrodlowe projektu w formacie CSV lub Excel. "
            "Mozesz wybrac zapisany plik weather history albo konkretny snapshot prognozy."
        ),
        "render": render_export_view,
    },
}


configure_page("Tatry Weather Dashboard")

if "active_view" not in st.session_state:
    st.session_state["active_view"] = "risk"

active_view = st.session_state.get("active_view", "risk")
if active_view not in VIEW_CONFIG:
    active_view = "risk"
    st.session_state["active_view"] = active_view

render_app_header(VIEW_CONFIG[active_view]["description"])
render_top_nav(active_view)
VIEW_CONFIG[active_view]["render"]()
