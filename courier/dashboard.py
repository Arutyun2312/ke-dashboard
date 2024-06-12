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
        st.title('Select a Dashboard')
        section = st.radio('Section', tuple(Section), format_func=lambda s: s.label)

        if section not in [Section.intro, Section.movielens_4, Section.movielens_5]:
            st.title('Filters')

        if section not in [Section.intro, Section.region_performance, Section.movielens_4, Section.movielens_5]:
            courier_ids = [None] + sorted(df['courier_id'].unique())
            courier_id = st.selectbox('Courier ID?', courier_ids, format_func=lambda id: '-' if id is None else id)
        else:
            courier_id = None

        if section not in [Section.intro, Section.courier_performance, Section.region_performance, Section.courier_route, Section.movielens_4, Section.movielens_5]:
            region_ids = [None] + sorted(df['region_id'].unique())
            region_id = st.selectbox('Region ID?', region_ids, format_func=lambda id: '-' if id is None else id)
        else:
            region_id = None

        if section not in [Section.intro, Section.courier_performance, Section.movielens_4, Section.movielens_5]:
            months = [None] + list(range(1, 13))
            month = st.selectbox('Month?', months, format_func=lambda m: '-' if m is None else list(calendar.month_name)[m])
        else:
            month = None

        if month is not None and section not in [Section.intro, Section.region_performance, Section.courier_performance, Section.movielens_4, Section.movielens_5]:
            days = [None] + list(range(1, 32))
            day = st.selectbox('Day?', days, format_func=lambda d: '-' if d is None else str(d).rjust(2, '0'))
        else:
            day = None

    if section != Section.intro:
        st.title(section.label)

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

            df, _, _ = delivery_df()
            if month is not None:
                df = df[df['delivery_gps_time'].dt.month == int(month)]

            centroids = df.groupby('region_id').agg({
                'lat': 'mean',
                'lng': 'mean',
                'order_id': 'count'
            }).reset_index()

            centroids.columns = ['id', 'lat', 'lng', 'count']

            st.write("### Deliveries by Region")
            st.write("This geochart shows the distribution of deliveries across different regions. Each point represents a region where the courier made deliveries, with the size of the point indicating the number of deliveries.")
            model.geochart(centroids, 'No. deliveries')
        else:
            util.write_empty('Cannot show this section with the given filters. Please remove day or month filters')

    if section == Section.courier_performance:
        if courier_id is not None:
            model.dashboard2(courier_id)
        else:
            util.write_empty('Cannot show this section with the given filters. Please select a courier')

    if section == Section.courier_route:
        if courier_id is not None and month is not None and day is not None:
            route = list(map(tuple, df[['delivery_gps_lat', 'delivery_gps_lng']].values))
            st.subheader(f'Route Inspection')
            if len(route):
                df_route = df[(df['courier_id'] == courier_id) & (df['delivery_gps_time'].dt.month == month) & (df['delivery_gps_time'].dt.day == day)]
                 # Calculate total and optimized distances
                distance, optimized_distance = distance_df[(distance_df['courier_id'] == courier_id) & (distance_df['month'] == month) & (distance_df['day'] == day)][['distance', 'optimized_distance']].values[0]
                wasted_distance = distance - optimized_distance
                areas = list(df_route['region_id'].unique())

                # Display the metrics
                col1, col2, col3, col4 = st.columns(4)
                col1.metric(label="Distance Traveled (km)", value=round(distance, 2), help='Total distance traveled')
                col2.metric(label="Optimized Routes Distance (km)", value=round(optimized_distance, 2), help='Distance traveled if courier traveled by efficient route')
                col3.metric(label="Wasted Distance (km)", value=round(wasted_distance, 2), help='Extra distance traveled')
                col4.metric(label="Regions", value='[' + ','.join(list(map(str, areas))) + ']', help='List of visited regions')

                # Prepare the route data for mapping
                df_route = df_route[['delivery_gps_lat', 'delivery_gps_lng', 'delivery_gps_time']]
                df_route.columns = ['lat', 'lng', 'time']
                df_route = df_route.sort_values('time')

                # Calculate cumulative distance
                df_route['prev_lat'] = df_route['lat'].shift()
                df_route['prev_lng'] = df_route['lng'].shift()
                df_route = df_route.dropna()
                df_route['distance'] = df_route.apply(lambda row: util.haversine(row['prev_lat'], row['prev_lng'], row['lat'], row['lng']), axis=1)
                df_route['cumulative_distance'] = df_route['distance'].cumsum()
            
                col1, col2 = st.columns(2)

                with col1:
                    # Line chart for distance covered over time
                    st.write("### Distance Covered Over Time")
                    st.write("This line chart shows the cumulative distance covered by the courier over time, aggregated per hour.")
                    df_route['hour'] = df_route['time'].dt.hour
                    distance_over_time = df_route.groupby('hour')['cumulative_distance'].max().reset_index()
                    distance_chart = alt.Chart(distance_over_time).mark_line().encode(
                        x=alt.X('hour:Q', title='Hour of Day'),
                        y=alt.Y('cumulative_distance:Q', title='Cumulative Distance Covered (km)'),
                        tooltip=['hour:Q', 'cumulative_distance:Q']
                    ).properties(
                        title="Distance Covered Over Time"
                    )
                    st.altair_chart(distance_chart, use_container_width=True)

                with col2:
                    # Line chart for total number of deliveries over time
                    st.write("### Total Number of Deliveries Over Time")
                    st.write("This line chart shows the total number of deliveries made by the courier over time, aggregated per hour.")
                    deliveries_over_time = df_route.groupby('hour').size().cumsum().reset_index(name='count')
                    deliveries_chart = alt.Chart(deliveries_over_time).mark_line().encode(
                        x=alt.X('hour:Q', title='Hour of Day'),
                        y=alt.Y('count:Q', title='Number of Deliveries'),
                        tooltip=['hour:Q', 'count:Q']
                    ).properties(
                        title="Total Number of Deliveries Over Time"
                    )
                    st.altair_chart(deliveries_chart, use_container_width=True)

                # Create a Folium map
                m = folium.Map(location=[df_route['lat'].mean(), df_route['lng'].mean()], zoom_start=14)

                # Add the delivery points and route
                folium.PolyLine(df_route[['lat', 'lng']].values, color='blue').add_to(m)
                # Add first and last markers with different colors
                first_point = df_route.iloc[0]
                last_point = df_route.iloc[-1]
                folium.Marker(
                    location=[first_point['lat'], first_point['lng']],
                    popup=f"Start: {first_point['time']}",
                    icon=folium.Icon(color='green')
                ).add_to(m)
                folium.Marker(
                    location=[last_point['lat'], last_point['lng']],
                    popup=f"End: {last_point['time']}",
                    icon=folium.Icon(color='red')
                ).add_to(m)
                
                # Add remaining markers
                for i, row in df_route.iloc[1:-1].iterrows():
                    folium.Marker(
                        location=[row['lat'], row['lng']],
                        popup=row['time']
                    ).add_to(m)

                # Title for the Streamlit app
                st.title('Delivery Route Visualization')
                # Display the map in Streamlit
                st_folium(m, use_container_width=True)
            else:
                st.subheader('No graph available. Courier did not drive this day 😢')
        else:
            util.write_empty('Cannot show this section with the given filters. Please select a courier, month and day. Try 164, June, 04')
    
    if section == Section.movielens_4:
        import movie.model
        movie.model.dashboard4()

    if section == Section.movielens_5:
        import movie.model
        movie.model.dashboard5()

    if util.isDev() and section == Section.experimental:
        df, _, _ = model.delivery_df()

        centroids = df.groupby('region_id').agg({
            'lat': 'mean',
            'lng': 'mean',
            'order_id': 'count'
        }).reset_index()

        centroids.columns = ['id', 'lat', 'lng', 'count']

        model.geochart(centroids, 'No. deliveries')