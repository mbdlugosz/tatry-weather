from __future__ import annotations

import streamlit as st

from dashboard_utils import configure_page, render_hero, render_panel


configure_page("Tatry Weather Dashboard")

render_hero(
    "Tatry Weather Dashboard",
    "Dashboard do analizy przestrzennych danych pogodowych i jakosci powietrza dla obszaru Tatr. "
    "Aplikacja prezentuje dane historyczne z SQLite oraz najnowsza prognoze z plikow JSON.",
)

col1, col2 = st.columns([1.25, 1])
with col1:
    render_panel(
        "Zakres dashboardu",
        "Strona Dane historyczne pokazuje zapisane pomiary temperatury, temperatury odczuwalnej, "
        "cisnienia, wilgotnosci i PM10. Strona Prognoza pogody prezentuje najnowszy rozklad temperatur "
        "dla kolejnych terminow prognozy.",
    )
with col2:
    render_panel(
        "Uruchomienie",
        "Uruchom aplikacje poleceniem `uv run streamlit run app.py`. "
        "Nawigacja stron znajduje sie w panelu bocznym po lewej stronie.",
    )

st.caption("Dashboard filtruje dane do aktualnego obszaru wspolrzednych zdefiniowanego dla projektu.")
