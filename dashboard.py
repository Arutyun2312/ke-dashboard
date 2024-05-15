from enum import StrEnum
import streamlit as st


class DashboardType(StrEnum):
    courier = 'Courier'
    movie = 'Movie'


with st.sidebar:
    st.title('Navigation')
    add_radio = st.radio(
        "Choose a dashboard",
        (DashboardType.courier, DashboardType.movie)
    )


