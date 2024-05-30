import calendar
from functools import reduce
import json
import folium
import pandas as pd
import requests
import streamlit as st
from courier.model import delivery_df
import util
import streamlit.components.v1 as components
import altair as alt
import courier.model as model
from .model import Section
from streamlit_folium import st_folium

def run():
    st.html("""
    <style>
    div[data-testid=stMetric] {
        box-shadow: rgba(99, 99, 99, 0.2) 0px 2px 8px 0px;
        border-radius: 10px;
        padding: 20px;
    }
    </style>
    """)
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
        st.title('Courier Dashboard Section')
        section = st.radio('Section', tuple(Section), format_func=lambda s: s.label)

        if section not in [Section.intro]:
            st.title('Filters')

        if section not in [Section.intro, Section.courier_table]:
            courier_ids = [None] + sorted(df['courier_id'].unique())
            courier_id = st.selectbox('Courier ID?', courier_ids, format_func=lambda id: '-' if id is None else id)
        else:
            courier_id = None

        if section not in [Section.intro, Section.courier_performance, Section.courier_table, Section.region_performance, Section.courier_route]:
            region_ids = [None] + sorted(df['region_id'].unique())
            region_id = st.selectbox('Region ID?', region_ids, format_func=lambda id: '-' if id is None else id)
        else:
            region_id = None

        if section not in [Section.intro]:
            months = [None] + list(range(1, 13))
            month = st.selectbox('Month?', months, format_func=lambda m: '-' if m is None else list(calendar.month_name)[m])
        else:
            month = None

        if month is not None and section not in [Section.intro, Section.courier_performance, Section.courier_table]:
            days = [None] + list(range(1, 32))
            day = st.selectbox('Day?', days, format_func=lambda d: '-' if d is None else str(d).rjust(2, '0'))
        else:
            day = None

    if section != Section.intro:
        st.title(f'Courier dashboard')

    if section == Section.intro:
        st.write("""
        # Welcome to the Courier Dashboard! 👋

        Here, you can delve into detailed insights about our couriers' performance. The dashboard is designed to provide you with a comprehensive view, enabling informed decision-making to optimize operations. Below are the sections available for your analysis:

        ## Region Performance

        This section presents two informative bar charts:
        1. **Number of Deliveries per Region**: Visualize the distribution of deliveries across various regions.
        2. **Average Duration of a Delivery per Region**: Assess the efficiency of deliveries in different regions.

        Additionally, you can see the count of active and inactive couriers, offering a useful metric to understand workforce utilization.

        ### Decisions Possible:
        - Identify regions with high delivery volumes to allocate more resources.
        - Detect regions with longer delivery durations to investigate potential delays.
        - Evaluate the number of inactive couriers to strategize on reactivation or replacement.

        ## Courier Performance

        Here, you can track the number of deliveries over time. By selecting a specific month, you can view detailed delivery counts for that period.

        ### Decisions Possible:
        - Monitor delivery trends over time to forecast future demands.
        - Identify peak delivery periods to plan for additional staffing.
        - Analyze month-over-month performance to recognize improvement or decline.

        ## Courier Route Inspection

        This section provides critical metrics such as:
        - **Visited Regions**: Track the regions each courier has visited.
        - **Distance Traveled**: Measure the total distance covered.
        - **Expected Distance to Travel**: Compare the planned versus actual distance.
        - **Distance Wasted**: Identify inefficiencies by tracking unnecessary travel distances.

        ### Decisions Possible:
        - Optimize route planning to reduce wasted distances and improve efficiency.
        - Analyze visited regions to ensure balanced coverage and prevent overload in certain areas.
        - Adjust expected distance metrics based on real-world data to refine planning accuracy.

        ## Courier Table

        View raw data in a comprehensive dataframe format. This data includes the number of deliveries and uniquely visited regions. You can select specific months and days to focus on particular time ranges.

        ### Decisions Possible:
        - Perform granular analysis on delivery counts and regions to identify patterns or anomalies.
        - Customize time range views to assess daily or monthly performance for targeted decision-making.
        - Leverage raw data for deeper statistical analysis and custom reporting.

        We hope you find this dashboard both informative and delightful as you steer your team towards greater efficiency and success!
        """)

    if section == Section.region_performance:
        st.subheader(section.label)
        if month is None or day is None:
            util.horizontal(
                lambda: model.overloaded_region_metric(courier_id, region_id, month, day) if day is None else None,
                *model.number_of_active_couriers(courier_id, region_id, month, day)
            )
            col1, col2 = st.columns(2)
            with col1:
                s1 = model.delivery_duration_chart(courier_id, region_id, month)
            with col2:
                s2 = model.deliveries_per_region(courier_id, region_id, month)
            if s1 == 0 or s2 == 0:
                util.write_empty('There are no deliveries with your selected filters. Try adjusting them')
            model.deliveries_per_day(courier_id, region_id, month)
        else:
            util.write_empty('Cannot show this section with the given filters. Please remove day or month filters')

    if section == Section.courier_performance:
        if courier_id is not None:
            df = util.multimask(
                df,
                (df['courier_id'] == courier_id) if courier_id is not None else None,
                (df['delivery_gps_time'].dt.month == int(month)) if month is not None else None,
                (df['delivery_gps_time'].dt.day == int(day)) if day is not None else None,
            )
            df = df.sort_values(['delivery_gps_time'])

            if month is None:
                model.deliveries_over_time(courier_id, region_id, month)
            else:
                def route_distance(day: int):
                    mask = (df['delivery_gps_time'].dt.day == day)
                    route = df[mask][['delivery_gps_lat', 'delivery_gps_lng']]
                    return util.calculate_total_distance(route)

                index=[day.rjust(2, '0') for day in map(str, util.day_iterator())]
                month_df = pd.DataFrame(list(map(route_distance, util.day_iterator())), index=index)
                if max(month_df[month_df.columns[0]]):
                    st.title('Distance (km) per Day')
                    st.bar_chart(month_df)
                else:
                    util.write_empty('No data available')
        else:
            util.write_empty('Cannot show this section with the given filters. Please select a courier')

    if section == Section.courier_route:
        if courier_id is not None and month is not None and day is not None:
            route = list(map(tuple, df[['delivery_gps_lat', 'delivery_gps_lng']].values))
            st.subheader(f'Route Inspection')
            if len(route):
                distance, optimized_distance = getDistance(courier_id, day, month).values[0]
                data = pd.DataFrame(
                    [courier_id, distance, optimized_distance, distance - optimized_distance, list(df.groupby('region_id').size().index)],
                    index=['Courier Id', 'Distance Traveled (km)', 'Optimized Routes Distance (km)', 'Wasted Distance (km)', 'Areas']
                )
                st.dataframe(data.T.round(2), hide_index=True)

                # Title for the Streamlit app
                st.title('Delivery Route Visualization')

                df_route = df[(df['courier_id'] == int(courier_id)) & (df['delivery_gps_time'].dt.month == int(month)) & (df['delivery_gps_time'].dt.day == int(day))]
                df_route = df_route[['delivery_gps_lat', 'delivery_gps_lng', 'delivery_gps_time']]
                df_route.columns = ['lat', 'lng', 'time']

                # Create a Folium map
                m = folium.Map(location=[df_route['lat'].mean(), df_route['lng'].mean()], zoom_start=14)

                # Add the delivery points and route
                folium.PolyLine(df_route[['lat', 'lng']].values, color='blue').add_to(m)
                for i, row in df_route.iterrows():
                    folium.Marker(
                        location=[row['lat'], row['lng']],
                        popup=row['time']
                    ).add_to(m)

                # Display the map in Streamlit
                st_folium(m, use_container_width=True)
            else:
                st.subheader('No graph available. Courier did not drive this day 😢')
        else:
            util.write_empty('Cannot show this section with the given filters. Please select a courier, month and day')

    if section == Section.courier_table:
        if courier_id is None:
            model.courier_list(courier_id, region_id, month)
        else:
            util.write_empty('Cannot show this section with the given filters. Please unselect the courier')

    if util.isDev() and section == Section.experimental:
        df, _, _ = model.delivery_df()

        centroids = df.groupby('region_id').agg({
            'lat': 'mean',
            'lng': 'mean',
            'order_id': 'count'
        }).reset_index()

        centroids.columns = ['id', 'lat', 'lng', 'count']

        model.geochart(centroids, 'No. deliveries')