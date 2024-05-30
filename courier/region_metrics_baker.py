import pandas as pd
import util

df = 'data/delivery_sh.csv'

df = pd.read_csv(df)
df['accept_time'] = util.to_datetime(df['accept_time'])
df['delivery_time'] = util.to_datetime(df['delivery_time'])
df['delivery_gps_time'] = util.to_datetime(df['delivery_gps_time'])
df['delivery_duration'] = (df['delivery_time'] - df['accept_time']).dt.total_seconds() / 3600

rows = []

for region_id in df['region_id'].unique():
    region_df = df[df['region_id'] == region_id].copy()
    region_df['day'] = region_df['delivery_gps_time'].dt.day
    region_df['month'] = region_df['delivery_gps_time'].dt.month

    grouped = region_df.groupby(['month', 'day'])

    days = set(list(util.day_month_iterator()))

    for (month, day), group in grouped:
        rows.append([region_id, month, day, group['courier_id'].unique()])
        days.remove((day, month))
    
    for day, month in days:
        rows.append([region_id, month, day, []])

pd.DataFrame(rows, columns=['region_id', 'month', 'day', 'couriers']).to_csv('data/delivery_region_metrics.csv', index=False)
