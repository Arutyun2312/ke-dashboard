from functools import reduce
import pandas as pd
import requests
import streamlit as st
from courier.model import delivery_df
import util
import streamlit.components.v1 as components
import altair as alt
from bs4 import BeautifulSoup
import courier.model as model

def run():
    dfs = delivery_df()
    df, distance_df, region_metric_df = [x.copy() for x in dfs]

    def getDistance(courier_id, day=None, month=None):
        mask = distance_df['courier_id'] == int(courier_id)
        if day is not None:
            mask = mask & (distance_df['day'] == int(day))
        if month is not None:
            mask = mask & (distance_df['month'] == int(month))
        return distance_df[mask][['distance', 'optimized_distance']]

    with st.sidebar:
        st.title('Filters')

        courier_ids = [None] + sorted(df['courier_id'].unique())
        courier_id = st.selectbox('Courier ID?', courier_ids)

        region_ids = [None] + sorted(df['region_id'].unique())
        region_id = st.selectbox('Region ID?', region_ids)

        months = [None] + [month.rjust(2, '0') for month in map(str, range(1, 13))]
        month = st.selectbox('Month?', months)

        if month is not None:
            days = [None] + [day.rjust(2, '0') for day in map(str, range(1, 32))]
            day = st.selectbox('Day?', days)
        else:
            day = None

    st.title(f'Courier dashboard')

    col1, col2, col3 = st.columns(3)
    with col1:
        model.overloaded_region_metric(courier_id, region_id, month, day)
    with col2:
        model.number_of_active_couriers(courier_id, region_id, month, day)
    with col3:
        pass

    if courier_id is None:
        st.title('Region-Based Delivery Performance')
        model.delivery_duration_chart(courier_id, region_id, month)

    df = util.multimask(
        df,
        (df['courier_id'] == courier_id) if courier_id is not None else None,
        (df['delivery_gps_time'].dt.month == int(month)) if month is not None else None,
        (df['delivery_gps_time'].dt.day == int(day)) if day is not None else None,
    )
    df = df.sort_values(['delivery_gps_time'])

    if month is None or day is None:
        st.title('Deliveries per Region')
        st.write('This bar chart shows the hottest regions')
        model.deliveries_per_region(courier_id, region_id, month)
        model.deliveries_per_day(courier_id, region_id, month)

    model.courier_list(courier_id, region_id, month)

    if courier_id is not None and month is None and day is None:
        model.deliveries_over_time(courier_id, region_id, month)


    if courier_id is not None and month is not None and day is None:
        def route_distance(day: int):
            mask = (df['delivery_gps_time'].dt.day == day)
            route = df[mask][['delivery_gps_lat', 'delivery_gps_lng']]
            return util.calculate_total_distance(route)

        index=[day.rjust(2, '0') for day in map(str, util.day_iterator())]
        month_df = pd.DataFrame(list(map(route_distance, util.day_iterator())), index=index)
        if max(month_df[month_df.columns[0]]):
            st.title('Distance (km) per Day')
            st.bar_chart(month_df)

    if courier_id is not None and month is not None and day is not None:
        route = list(map(tuple, df[['delivery_gps_lat', 'delivery_gps_lng']].values))
        st.title(f'Route Inspection')
        if len(route):
            getDistance = util.calculate_total_distance(route)
            optimized = util.nearest_neighbor(route)
            optimized_distance = util.calculate_total_distance(optimized)
            data = pd.DataFrame(
                [courier_id, getDistance, optimized_distance, getDistance - optimized_distance, list(df.groupby('region_id').size().index)], 
                index=['Courier Id', 'Distance Traveled (km)', 'Optimized Routes Distance (km)', 'Wasted Distance (km)', 'Areas']
            )
            st.dataframe(data.T.round(2), hide_index=True)
        else:
            st.subheader('Courier did not drive this day')
