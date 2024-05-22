import streamlit as st
import pandas as pd
import altair as alt
import util

@st.cache_data
def delivery_df():
    # df = util.get_csv('https://firebasestorage.googleapis.com/v0/b/friendly-8b1c0.appspot.com/o/delivery_sh.csv?alt=media&token=93b87698-b581-4cfb-a56b-1cc819c693fc')
    df = 'data/delivery_sh.csv'
    distance_df = 'data/delivery_courier_distances.csv'
    region_metric_df = 'data/delivery_region_metrics.csv'

    df = pd.read_csv(df)
    df['accept_time'] = pd.to_datetime(df['accept_time'], format='%m-%d %H:%M:%S')
    df['delivery_time'] = pd.to_datetime(df['delivery_time'], format='%m-%d %H:%M:%S')
    df['delivery_gps_time'] = pd.to_datetime(df['delivery_gps_time'], format='%m-%d %H:%M:%S')
    df['delivery_duration'] = (df['delivery_time'] - df['accept_time']).dt.total_seconds() / 3600  # Convert to hours

    distance_df = pd.read_csv(distance_df)
    region_metric_df = pd.read_csv(region_metric_df)
    return df, distance_df, region_metric_df

@st.cache_data
def get_region_performance(courier_id: str|None, region_id: str|None, month: str|None):
    df, _, _ = delivery_df()
    if month is not None:
        df = df[df['delivery_gps_time'].dt.month == int(month)]
    if courier_id is not None:
        df = df[df['courier_id'] == int(courier_id)]
    if region_id is not None:
        df = df[df['region_id'] == int(region_id)]
    return df.groupby('region_id')['delivery_duration'].mean().reset_index().round(2)


def overloaded_region_metric(courier_id: str|None, region_id: str|None, month: str|None, day: str|None):
    if day is not None:
        return
    region_performance = get_region_performance(courier_id, region_id, month)
    value = region_performance[region_performance['delivery_duration'] >= 5].index.size
    st.metric(
        label="No. Overloaded Regions",
        value=value,
        delta=value if value > 0 else None,
        delta_color="inverse",
        help='A courier spends more than 5 hours between each delivery'
    )

def number_of_active_couriers(courier_id: str|None, region_id: str|None, month: str|None, day: str|None):
    if courier_id is not None:
        return
    df, _, _ = delivery_df()
    if month is not None:
        df = df[df['delivery_gps_time'].dt.month == int(month)]
    if day is not None:
        df = df[df['delivery_gps_time'].dt.day == int(day)]
    if region_id is not None:
        df = df[df['region_id'] == int(region_id)]
    inactive = set(df['courier_id'].unique())
    inactive = inactive.difference(df['courier_id'].unique())
    active = df['courier_id'].unique().size
    ratio = 1 if active == 0 and len(inactive) == 0 else active / (len(inactive) + active) * 100 
    st.metric(
        label="Active/Inactive Couriers = Active Ratio",
        value=f'{active}/{len(inactive)} = {ratio:.1f}%',
        help='Active = delivered at least once. Inactive = never delivered. % shows ratio of active couriers'
    )

def number_of_inactive_couriers(month: str|None):
    df, _, _ = delivery_df()
    couriers = set(df['courier_id'].unique()).difference()
    if month is not None:
        df = df[df['delivery_gps_time'].dt.month == int(month)]
    couriers = couriers.difference(df['courier_id'].unique())
    st.metric(
        label="No. Active Couriers",
        value=len(couriers),
        help='Number of couriers that have delivered at least once'
    )

def delivery_duration_chart(courier_id: str|None, region_id: str|None, month: str|None):
    region_performance = get_region_performance(courier_id, region_id, month)
    region_performance.columns = ['Region ID', 'Average Delivery Duration (Hours)']
    chart = alt.Chart(region_performance).mark_bar().encode(
        x=alt.X('Region ID:O', title='Region ID'),
        y=alt.Y('Average Delivery Duration (Hours):Q', title='Average Delivery Duration (Hours)'),
        color=alt.Color('Average Delivery Duration (Hours):Q', scale=alt.Scale(scheme='reds'), legend=alt.Legend(title="Average Delivery Duration (Hours)")),
        tooltip=['Region ID', 'Average Delivery Duration (Hours)']
    ).properties(
        title='Average Delivery Duration by Region',
    )
    st.altair_chart(chart, use_container_width=True)

def deliveries_per_region(courier_id: str|None, region_id: str|None, month: str|None):
    df, _, _ = delivery_df()
    if month is not None:
        df = df[df['delivery_gps_time'].dt.month == int(month)]
    if courier_id is not None:
        df = df[df['courier_id'] == int(courier_id)]
    if region_id is not None:
        df = df[df['region_id'] == int(region_id)]

    deliveries = df.groupby(df['region_id']).size().reset_index()
    deliveries.columns = ['Region', 'Count']

    base = alt.Chart(deliveries).encode(
        x=alt.X('Region:N', title='Area'),
        tooltip=['Region']
    )

    deliveries_line = base.mark_bar().encode(
        y=alt.Y('Count:Q', title='No. Deliveries'),
        color=alt.Color('Count:Q', scale=alt.Scale(scheme='reds'), legend=alt.Legend(title="No. Deliveries")),
        tooltip=[alt.Tooltip('Region:N', title='Area'), alt.Tooltip('Count:Q', title='No. Deliveries')]
    ).interactive()

    st.altair_chart(deliveries_line, use_container_width=True)

def deliveries_per_day(courier_id: str|None, region_id: str|None, month: str|None):
    df, _, _ = delivery_df()
    if month is not None:
        df = df[df['delivery_gps_time'].dt.month == int(month)]
    if courier_id is not None:
        df = df[df['courier_id'] == int(courier_id)]
    if region_id is not None:
        df = df[df['region_id'] == int(region_id)]

    st.title(f'No. Deliveries')
    st.write('This line chart shows deliveries over time')
    deliveries = df.groupby(df['delivery_gps_time'].dt.date).size().reset_index()
    deliveries.columns = ['Date', 'Deliveries']
    
    # Create a base chart with common settings
    base = alt.Chart(deliveries).encode(
        x=alt.X('Date:T', title='Date'),
        tooltip=['Date']
    )

    deliveries_line = base.mark_line(
        color='blue',
        point=True
    ).encode(
        y=alt.Y('Deliveries:Q', title='No. Deliveries'),
        tooltip=[alt.Tooltip('Deliveries:Q', title='Deliveries')],
        color=alt.value('blue')  # Ensures the line color is blue
    ).interactive()

    st.altair_chart(deliveries_line, use_container_width=True)

def deliveries_over_time(courier_id: str|None, region_id: str|None, month: str|None):
    if region_id is not None:
        return
    _, distance_df, _ = delivery_df()
    def getDF():
        df = distance_df
        if month is not None:
            df = df[df['delivery_gps_time'].dt.month == int(month)]
        if courier_id is not None:
            df = df[df['courier_id'] == int(courier_id)]
        return df.groupby('month')['distance'].sum().values
    index = [month.rjust(2, '0') for month in map(str, util.month_iterator())]
    month_df = pd.DataFrame(getDF(), index=index)
    st.title('Distance per Month')
    month_df.reset_index(inplace=True)
    month_df.columns = ['Month', 'Distance']
    # Create the Altair chart object
    chart = alt.Chart(month_df).mark_bar().encode(
        x=alt.X('Month:N', title='Month'),
        y=alt.Y('Distance:Q', title='Distance (km)'),
        color=alt.Color('Distance:Q', scale=alt.Scale(scheme='reds'), legend=alt.Legend(title="Distance Traveled")),
        tooltip=[alt.Tooltip('Month:N', title='Month'), alt.Tooltip('Distance:Q', title='Distance Traveled')]
    ).properties(
        title="Monthly Distance Traveled"
    )

    # Display the chart using Streamlit
    st.altair_chart(chart, use_container_width=True)

def courier_list(courier_id: str|None, region_id: str|None, month: str|None):
    df, _, _ = delivery_df()
    if month is not None:
        df = df[df['delivery_gps_time'].dt.month == int(month)]
    if courier_id is not None:
        return
    if region_id is not None:
        df = df[df['region_id'] == int(region_id)]

    df = df.reset_index()

    st.title('Courier Metrics')
    st.write('This table shows metrics per courier')
    courier_metrics = df.groupby('courier_id').agg(
        Total_Deliveries=pd.NamedAgg(column='order_id', aggfunc='count'),
        Unique_Regions=pd.NamedAgg(column='region_id', aggfunc='nunique')
    )
    courier_metrics.columns = ['Total Deliveries', 'Occupied Regions']
    st.dataframe(courier_metrics, use_container_width=True)