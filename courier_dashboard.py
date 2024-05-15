from functools import reduce
import pandas as pd
import streamlit as st
import util
import streamlit.components.v1 as components
import altair as alt

def run():
    # Cache the data fetching and processing to optimize performance
    @st.cache_data
    def delivery_df():
        # df = util.get_csv('https://firebasestorage.googleapis.com/v0/b/friendly-8b1c0.appspot.com/o/delivery_sh.csv?alt=media&token=93b87698-b581-4cfb-a56b-1cc819c693fc')
        df = 'data/delivery_sh.csv'

        df = pd.read_csv(df)
        df['delivery_gps_time'] = df['delivery_gps_time'].apply(lambda d : '2023-' + d)
        df['delivery_gps_time'] = pd.to_datetime(df['delivery_gps_time'])
        return df

    # Dialog to apply filters on courier ID, month, and day
    @st.experimental_dialog("Filter")
    def showFilters(df: pd.DataFrame):
        courier_ids = [None] + sorted(df['courier_id'].unique()[1:])
        courier_id = st.selectbox('Courier ID?', courier_ids, index=courier_ids.index(st.session_state.courier_id))
        if courier_id is not None:
            months = [None] + [month.rjust(2, '0') for month in map(str, range(1, 13))]
            month = st.selectbox('Month?', months, index=months.index(st.session_state.month))
        else:
            month = None
        if month:
            days = [None] + [day.rjust(2, '0') for day in map(str, range(1, 32))]
            day = st.selectbox('Day?', days, index=days.index(st.session_state.day))
        else:
            day = None

        if st.button('Apply'):
            st.session_state.courier_id = courier_id
            st.session_state.month = month
            st.session_state.day = day
            st.session_state.camera = False
            st.rerun()

    # Dialog for camera input
    @st.experimental_dialog('Camera')
    def cameraInput():
        img_buffer = st.camera_input('Take a picture')
        data = util.parseBarcode(img_buffer)
        if data:
            st.session_state.courier_id, st.session_state.day, st.session_state.month = data
            st.rerun()
        else:
            st.toast('Data invalid')

    # Dialog to show route on map
    @st.experimental_dialog('Route')
    def showRoute(df: pd.DataFrame):
        st.map(df, latitude='col1', longitude='col2')

    # Initialize session state with default values if not present
    def initialState(key: str, value=None):
        if key not in st.session_state:
            st.session_state[key] = value

    initialState('camera', False)
    initialState('courier_id')
    initialState('month')
    initialState('day')

    courier_id = st.session_state.courier_id
    month = st.session_state.month
    day = st.session_state.day

    st.title(f'Courier dashboard')

    df = delivery_df().copy()

    col1, col2 = st.columns(2)

    with col1:
        if st.button('Show Filters'):
            showFilters(df)

    with col2:
        if st.button('Get Courier from Barcode'):
            cameraInput()

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
            )

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
