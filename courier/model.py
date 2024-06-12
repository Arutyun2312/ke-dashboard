from enum import StrEnum, auto
import streamlit as st
import pandas as pd
import altair as alt
import util
import geopandas as gpd
import json

@st.cache_data
def __loading_delivery_df():
    if util.isDev():
        df = 'data/delivery_sh.csv'
        distance_df = 'data/delivery_courier_distances.csv'
        region_metric_df = 'data/delivery_region_metrics.csv'
    else:
        df = 'https://firebasestorage.googleapis.com/v0/b/friendly-8b1c0.appspot.com/o/delivery_sh.csv?alt=media&token=93b87698-b581-4cfb-a56b-1cc819c693fc'
        distance_df = 'https://firebasestorage.googleapis.com/v0/b/friendly-8b1c0.appspot.com/o/delivery_courier_distances.csv?alt=media&token=9b414540-5afa-4794-948a-449866e1196c'
        region_metric_df = 'https://firebasestorage.googleapis.com/v0/b/friendly-8b1c0.appspot.com/o/delivery_region_metrics.csv?alt=media&token=734a4dc3-3ceb-482c-b4b7-2e3ff7fe7e02'

    df = pd.read_csv(df)
    df['accept_time'] = pd.to_datetime(df['accept_time'], format='%m-%d %H:%M:%S')
    df['delivery_time'] = pd.to_datetime(df['delivery_time'], format='%m-%d %H:%M:%S')
    df['delivery_gps_time'] = pd.to_datetime(df['delivery_gps_time'], format='%m-%d %H:%M:%S')
    df['delivery_duration'] = (df['delivery_time'] - df['accept_time']).dt.total_seconds() / 3600  # Convert to hours

    distance_df = pd.read_csv(distance_df)
    region_metric_df = pd.read_csv(region_metric_df)
    return df, distance_df, region_metric_df

def delivery_df():
    return [df.copy() for df in __loading_delivery_df()]

@st.cache_data
def region_centers():
    df, _, _ = delivery_df()

    centroids = df.groupby('region_id').agg({
        'lat': 'mean',
        'lng': 'mean'
    }).reset_index()
    centroids.columns = ['region_id', 'lat', 'lng']

    return centroids


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

class Section(StrEnum):
    intro = auto()
    region_performance = auto()
    courier_performance = auto()
    courier_route = auto()
    movielens_4 = auto()
    movielens_5 = auto()
    if util.isDev():
        experimental = auto()

    @property
    def label(self):
        if self == Section.intro:
            return 'Introduction'
        if self == Section.region_performance:
            return 'Region Performance'
        if self == Section.courier_performance:
            return 'Courier Performance'
        if self == Section.courier_route:
            return 'Courier Route Inspection'
        if self == Section.movielens_4:
            return 'MovieLens User Engagement'
        if self == Section.movielens_5:
            return 'MovieLens Movie Performance'
        if util.isDev() and self == Section.experimental:
            return 'Experimental'

def overloaded_region_metric(courier_id: str|None, region_id: str|None, month: str|None, day: str|None):
    if day is not None:
        return
    region_performance = get_region_performance(courier_id, region_id, month)
    value = region_performance[region_performance['delivery_duration'] >= 5].index.size
    st.metric(
        label="No. Overloaded Regions",
        value=value,
        help='A courier spends more than 5 hours between each delivery'
    )

def number_of_active_couriers(courier_id: str|None, region_id: str|None, month: str|None, day: str|None):
    if courier_id is not None:
        return [None] * 3
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
    ratio = 0 if active == 0 and len(inactive) == 0 else active / (len(inactive) + active) * 100
    return (
        lambda : st.metric(
            label="Active Couriers",
            value=f'{active}',
            help='Number of couriers that have delivered at least once'
        ),
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
    if courier_id is not None:
        return
    region_performance = get_region_performance(courier_id, region_id, month)
    region_performance.columns = ['Region ID', 'Duration (Hours)']
    chart = alt.Chart(region_performance).mark_bar().encode(
        x=alt.X('Region ID:O', title='Region ID'),
        y=alt.Y('Duration (Hours):Q', title='Duration (Hours)'),
        color=alt.Color('Duration (Hours):Q', scale=alt.Scale(scheme='reds'), legend=None),
        tooltip=['Region ID', 'Duration (Hours)']
    ).properties(
        title='Average Delivery Duration by Region',
    )

    if region_performance.size:
        st.altair_chart(chart, use_container_width=True)

    return region_performance.size

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
        color=alt.Color('Count:Q', scale=alt.Scale(scheme='reds'), legend=None),
        tooltip=[alt.Tooltip('Region:N', title='Area'), alt.Tooltip('Count:Q', title='No. Deliveries')]
    ).properties(
        title='No. Deliveries per Region',
    )

    if deliveries.size:
        st.altair_chart(deliveries_line, use_container_width=True)

    return deliveries.size

def deliveries_per_day(courier_id: str|None, region_id: str|None, month: str|None):
    df, _, _ = delivery_df()
    if month is not None:
        df = df[df['delivery_gps_time'].dt.month == int(month)]
    if courier_id is not None:
        df = df[df['courier_id'] == int(courier_id)]
    if region_id is not None:
        df = df[df['region_id'] == int(region_id)]

    st.write("""
    ## No. Deliveries
    This line chart shows deliveries over time
    """)
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
    if region_id is not None:
        df = df[df['region_id'] == int(region_id)]

    df = df.reset_index()
    courier_metrics = df.groupby('courier_id').agg(
        Total_Deliveries=pd.NamedAgg(column='order_id', aggfunc='count'),
        Unique_Regions=pd.NamedAgg(column='region_id', aggfunc='nunique')
    )
    courier_metrics.index.name = 'Courier ID'
    courier_metrics.columns = ['Total Deliveries', 'Occupied Regions']

    st.write(f"""
    This table shows metrics per courier.

    Total Deliveries = total number of deliveries

    Occupied Regions = total number of regions that courier has visited at least once
    """)
    st.dataframe(courier_metrics, use_container_width=True)

@st.cache_data
def shanghai_geojson_features():
    shanghai_geojson_url = 'https://geo.datav.aliyun.com/areas/bound/310000_full.json'
    shanghai_geojson = gpd.read_file(shanghai_geojson_url)
    shanghai_geojson = json.loads(shanghai_geojson.to_json())
    return alt.Data(values=shanghai_geojson['features'])

def geochart(df: pd.DataFrame, legend_title: str):
    # df.columns = ['id', 'lat', 'lng', 'count']

    background = alt.Chart(shanghai_geojson_features()).mark_geoshape(
        fill='#ECFFEB',
        stroke='darkblue'
    ).encode(
        tooltip=[alt.Tooltip('properties.name:N', title='Name')]
    ).project(
        type='mercator'
    ).properties(
        width=800,
        height=600
    ).interactive()

    points = alt.Chart(df).mark_circle().encode(
        longitude='lng:Q',
        latitude='lat:Q',
        size=alt.Size('count:Q', scale=alt.Scale(range=[100, 1000])),
        color=alt.Color('count:Q', scale=alt.Scale(scheme='viridis'), legend=alt.Legend(title=legend_title)),
        tooltip=['id:N', 'lat:Q', 'lng:Q', 'count:Q']
    )

    st.altair_chart(background + points, use_container_width=True)

def dashboard2(courier_id: int):
    import streamlit as st
    import pandas as pd
    import altair as alt

    # Load data using the pre-defined function
    df, distance_df, _ = delivery_df()

    # Assume a specific courier ID for the dashboard

    # Filter data for the selected courier
    courier_data = df[df['courier_id'] == courier_id]
    courier_distance_data = distance_df[distance_df['courier_id'] == courier_id]

    # Calculate number of deliveries made
    num_deliveries = courier_data.shape[0]

    # Calculate number of regions visited
    num_regions_visited = courier_data['region_id'].nunique()

    # Calculate working vs non-working days
    courier_data['date'] = courier_data['accept_time'].dt.date
    working_days = courier_data['date'].nunique()
    total_days = (courier_data['date'].max() - courier_data['date'].min()).days + 1
    non_working_days = total_days - working_days

    # Geochart data preparation
    region_deliveries = courier_data.groupby('region_id').size().reset_index(name='count')
    geochart_data = region_deliveries.merge(region_centers()[['region_id', 'lat', 'lng']], on='region_id')

    # Metrics in one row
    col1, col2 = st.columns(2)
    col1.metric(label="Number of Deliveries", value=num_deliveries, help="Total number of deliveries made by the courier.")
    col2.metric(label="Number of Regions Visited", value=num_regions_visited, help="Total number of unique regions visited by the courier.")

    col1, col2 = st.columns(2)

    with col1:
        # Geochart of deliveries in regions
        st.write("### Deliveries by Region")
        st.write("This geochart shows the distribution of deliveries across different regions. Each point represents a region where the courier made deliveries, with the size of the point indicating the number of deliveries.")
        geochart(geochart_data, legend_title="Number of Deliveries")

    with col2:
        # Pie chart of working vs non-working days
        st.write("### Working vs Non-Working Days")
        st.write("This pie chart shows the distribution of working days versus non-working days for the courier.")
        pie_chart_data = pd.DataFrame({
            'Days': ['Working Days', 'Non-Working Days'],
            'Count': [working_days, non_working_days]
        })
        pie_chart = alt.Chart(pie_chart_data).mark_arc().encode(
            theta=alt.Theta(field='Count', type='quantitative'),
            color=alt.Color(field='Days', type='nominal'),
            tooltip=['Days', 'Count']
        ).properties(
            title="Working vs Non-Working Days"
        )
        st.altair_chart(pie_chart, use_container_width=True)

    # Bar chart of distance traveled per month
    st.write("### Distance Traveled per Month")
    st.write("This bar chart shows the total distance traveled by the courier each month.")
    deliveries_over_time(courier_id, None, None)

    courier_list(None, None, None)



