from enum import StrEnum, auto
import streamlit as st
import courier.dashboard
import movie.dashboard 


class DashboardType(StrEnum):
    courier = auto()
    movie = auto()


st.set_page_config(layout="wide")

# with st.sidebar:
#     st.title('Dashboard Navigation')
#     dashboardType = st.radio("Choose a dashboard", tuple(DashboardType))
dashboardType = DashboardType.courier

if dashboardType == DashboardType.courier:
    courier.dashboard.run()

if dashboardType == DashboardType.movie:
    movie.dashboard.run()

