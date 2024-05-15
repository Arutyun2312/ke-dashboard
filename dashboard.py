from enum import StrEnum
import streamlit as st
import courier_dashboard 
import movie_dashboard 


class DashboardType(StrEnum):
    courier = 'Courier'
    movie = 'Movie'


st.set_page_config(layout="wide")

with st.sidebar:
    st.title('Navigation')
    dashboardType = st.radio(
        "Choose a dashboard",
        (DashboardType.courier, DashboardType.movie)
    )

if dashboardType == DashboardType.courier:
    courier_dashboard.run()

if dashboardType == DashboardType.movie:
    movie_dashboard.run()

