from enum import StrEnum
import streamlit as st
import courier.dashboard
import movie.dashboard 


class DashboardType(StrEnum):
    courier = 'Courier'
    movie = 'Movie'


st.set_page_config(layout="wide")

with st.sidebar:
    st.title('Dashboard Navigation')
    dashboardType = st.radio(
        "Choose a dashboard",
        (DashboardType.courier, DashboardType.movie)
    )

if dashboardType == DashboardType.courier:
    courier.dashboard.run()

if dashboardType == DashboardType.movie:
    movie.dashboard.run()

