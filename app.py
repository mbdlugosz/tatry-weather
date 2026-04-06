from __future__ import annotations

import streamlit as st

from dashboard_utils import configure_page


configure_page("Tatry Weather Dashboard")
st.switch_page("pages/1_Dane_historyczne.py")
