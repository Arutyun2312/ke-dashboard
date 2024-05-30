import pandas as pd
import util

df = 'data/delivery_sh.csv'

df = pd.read_csv(df)
df['accept_time'] = util.to_datetime(df['accept_time'])
df['delivery_time'] = util.to_datetime(df['delivery_time'])
df['delivery_gps_time'] = util.to_datetime(df['delivery_gps_time'])
df['delivery_duration'] = (df['delivery_time'] - df['accept_time']).dt.total_seconds() / 3600

rows = []

for courier_id in df['courier_id'].unique():
    courier_df = df[df['courier_id'] == courier_id].copy()
    courier_df['day'] = courier_df['delivery_gps_time'].dt.day
    courier_df['month'] = courier_df['delivery_gps_time'].dt.month
    
    grouped = courier_df.groupby(['month', 'day'])

    days = set(list(util.day_month_iterator()))
    
    for (month, day), group in grouped:
        route = group[['delivery_gps_lat', 'delivery_gps_lng']]
        distance = util.calculate_total_distance(route)
        optimized_route = util.nearest_neighbor(list(map(tuple, route.values)))
        optimized_distance = util.calculate_total_distance(optimized_route)
        rows.append([courier_id, month, day, group['region_id'].unique()[0], distance, optimized_distance])
        days.remove((day, month))
    
    for day, month in days:
        rows.append([courier_id, month, day, None, 0, 0])

pd.DataFrame(rows, columns=['courier_id', 'month', 'day', 'regions', 'distance', 'optimized_distance']).to_csv('data/delivery_courier_distances.csv', index=False)
