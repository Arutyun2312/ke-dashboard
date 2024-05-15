from functools import reduce
import pandas as pd
import requests
import streamlit as st
import util
import streamlit.components.v1 as components
import altair as alt
from bs4 import BeautifulSoup

def run():
    # Cache the data fetching and processing to optimize performance
    @st.cache_data
    def delivery_df():
        df = util.get_csv('https://firebasestorage.googleapis.com/v0/b/friendly-8b1c0.appspot.com/o/delivery_sh.csv?alt=media&token=93b87698-b581-4cfb-a56b-1cc819c693fc')
        # df = 'data/delivery_sh.csv'

        df = pd.read_csv(df)
        df['accept_time'] = pd.to_datetime(df['accept_time'], format='%m-%d %H:%M:%S')
        df['delivery_time'] = pd.to_datetime(df['delivery_time'], format='%m-%d %H:%M:%S')
        df['delivery_gps_time'] = pd.to_datetime(df['delivery_gps_time'], format='%m-%d %H:%M:%S')
        df['delivery_duration'] = (df['delivery_time'] - df['accept_time']).dt.total_seconds() / 3600  # Convert to hours
        return df

    # Dialog to show route on map
    @st.experimental_dialog('Route')
    def showRoute(df: pd.DataFrame):
        st.map(df, latitude='col1', longitude='col2')

    # Initialize session state with default values if not present
    def initialState(key: str, value=None):
        if key not in st.session_state:
            st.session_state[key] = value

    initialState('camera', False)

    df = delivery_df().copy()

    st.title(f'Courier dashboard')

    # Streamlit App
    st.title("Courier Idle Time Analysis")

    st.write("This application visualizes the idle times of couriers between deliveries.")

    # Group by region and calculate average delivery duration
    region_performance = df.groupby('region_id')['delivery_duration'].mean().reset_index().round(2)
    st.metric(label="No. Overloaded Regions", value=region_performance[region_performance['delivery_duration'] >= 5].index.size, delta=-0.5, delta_color="inverse", help='WHYHUYHWYWH')

    # Streamlit app
    st.title('Region-Based Delivery Performance')

    # Rename columns for clarity
    region_performance.columns = ['Region ID', 'Average Delivery Duration (Hours)']
    # Create the Altair chart
    chart = alt.Chart(region_performance).mark_bar().encode(
        x=alt.X('Region ID:O', title='Region ID'),
        y=alt.Y('Average Delivery Duration (Hours):Q', title='Average Delivery Duration (Hours)'),
        color=alt.Color('Average Delivery Duration (Hours):Q', scale=alt.Scale(scheme='reds'), legend=alt.Legend(title="Average Delivery Duration (Hours)")),
        tooltip=['Region ID', 'Average Delivery Duration (Hours)']
    ).properties(
        title='Average Delivery Duration by Region',
    )

    # Display the chart
    st.altair_chart(chart, use_container_width=True)

    with st.sidebar:
        st.title('Filters')

        courier_ids = [None] + sorted(df['courier_id'].unique()[1:])
        courier_id = st.selectbox('Courier ID?', courier_ids)

        if courier_id is not None:
            months = [None] + [month.rjust(2, '0') for month in map(str, range(1, 13))]
            month = st.selectbox('Month?', months)
        else:
            month = None

        if month is not None:
            days = [None] + [day.rjust(2, '0') for day in map(str, range(1, 32))]
            day = st.selectbox('Day?', days)
        else:
            day = None

    # Apply filters to data
    mask = [
        (df['courier_id'] == courier_id) if courier_id is not None else None,
        (df['delivery_gps_time'].dt.month == int(month)) if month is not None else None,
        (df['delivery_gps_time'].dt.day == int(day)) if day is not None else None,
    ]
    mask = [x for x in mask if x is not None]
    df = reduce(lambda df, mask: df[mask], mask, df)
    df = df.sort_values(['delivery_gps_time'])

    if month is None or day is None:
        col1, col2 = st.columns(2)
        with col1:
            st.title('Deliveries per Area')
            st.write('This bar chart shows the hottest areas')

            # Group by 'region_id', count deliveries, and reset the index
            deliveries = df.groupby(df['region_id']).size().reset_index()
            deliveries.columns = ['Region', 'Count']
            deliveries = deliveries.sort_values(by='Count', ascending=False)

            # Create a base chart with common settings
            base = alt.Chart(deliveries).encode(
                x=alt.X('Region:N', title='Area', sort='-y'),  # Sorting by 'y' value in descending order
                tooltip=['Region']
            )

            # Create a bar chart for cumulative deliveries
            deliveries_line = base.mark_bar().encode(
                y=alt.Y('Count:Q', title='No. Deliveries'),
                color=alt.Color('Count:Q', scale=alt.Scale(scheme='reds'), legend=alt.Legend(title="No. Deliveries")),
                tooltip=[alt.Tooltip('Region:N', title='Area'), alt.Tooltip('Count:Q', title='No. Deliveries')]
            ).interactive()

            st.altair_chart(deliveries_line, use_container_width=True)

        with col2:
            st.title(f'No. Deliveries per {"day" if month else "month"}')
            st.write('This line chart shows deliveries over time')
            deliveries = df.groupby(df['delivery_gps_time'].dt.date).size().reset_index()
            deliveries.columns = ['Date', 'Cumulative Deliveries']
            
            # Create a base chart with common settings
            base = alt.Chart(deliveries).encode(
                x=alt.X('Date:T', title='Date'),
                tooltip=['Date']
            )

            deliveries_line = base.mark_line(
                color='blue',
                point=True
            ).encode(
                y=alt.Y('Cumulative Deliveries:Q', title='Cumulative Deliveries'),
                tooltip=[alt.Tooltip('Cumulative Deliveries:Q', title='Cumulative Deliveries')],
                color=alt.value('blue')  # Ensures the line color is blue
            ).interactive()

            st.altair_chart(deliveries_line, use_container_width=True)

    if courier_id is None:
        st.title('Courier Metrics')
        st.write('This table shows metrics per courier')
        courier_metrics = df.groupby('courier_id').agg(
            Total_Deliveries=pd.NamedAgg(column='order_id', aggfunc='count'),
            Unique_Regions=pd.NamedAgg(column='region_id', aggfunc='nunique')
        )
        st.dataframe(courier_metrics, use_container_width=True)

    if courier_id is not None and month is None and day is None:
        def getDF():
            sum = []
            for day, month in util.day_month_iterator():
                if day == 1:
                    sum += [0]
                mask = (df['delivery_gps_time'].dt.month == month) & (df['delivery_gps_time'].dt.day == day)
                route = df[mask][['delivery_gps_lat', 'delivery_gps_lng']]
                sum[-1] += util.calculate_total_distance(route)
            return sum
        index = [month.rjust(2, '0') for month in map(str, util.month_iterator())]
        month_df = pd.DataFrame(getDF(), index=index)
        st.title('Distance per Month')
        month_df.reset_index(inplace=True)
        month_df.columns = ['Month', 'Distance']
        # Create the Altair chart object
        chart = alt.Chart(month_df).mark_bar().encode(
            x=alt.X('Month:N', title='Month'),
            y=alt.Y('Distance:Q', title='Distance Traveled'),
            color=alt.Color('Distance:Q', scale=alt.Scale(scheme='bluepurple'), legend=alt.Legend(title="Distance Traveled")),
            tooltip=[alt.Tooltip('Month:N', title='Month'), alt.Tooltip('Distance:Q', title='Distance Traveled')]
        ).properties(
            title="Monthly Distance Traveled"
        )

        # Display the chart using Streamlit
        st.altair_chart(chart, use_container_width=True)


    if courier_id is not None and month is not None and day is None:
        def route_distance(day: int):
            mask = (df['delivery_gps_time'].dt.day == day)
            route = df[mask][['delivery_gps_lat', 'delivery_gps_lng']]
            return util.calculate_total_distance(route)

        index=[day.rjust(2, '0') for day in map(str, util.day_iterator())]
        month_df = pd.DataFrame(list(map(route_distance, util.day_iterator())), index=index)
        if max(month_df[month_df.columns[0]]):
            st.title('Distance per Day')
            st.bar_chart(month_df)

    if courier_id is not None and month is not None and day is not None:
        route = list(map(tuple, df[['delivery_gps_lat', 'delivery_gps_lng']].values))
        st.title(f'Route Inspection')
        if len(route):
            distance = util.calculate_total_distance(route)
            optimized = util.nearest_neighbor(route)
            optimized_distance = util.calculate_total_distance(optimized)
            data = pd.DataFrame(
                [courier_id, distance, optimized_distance, distance - optimized_distance, list(df.groupby('region_id').size().index)], 
                index=['Courier Id', 'Distance Traveled (km)', 'Optimized Routes Distance (km)', 'Wasted Distance (km)', 'Areas']
            )
            st.dataframe(data.T.round(2), hide_index=True)

            html = util.drawRoute(route)
            components.html(html, height=600)
        else:
            st.subheader('Courier did not drive this day')
