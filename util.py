from functools import reduce
from io import StringIO
import numpy as np
from PIL import Image
import pandas as pd
import requests
import streamlit as st


def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    r = 6371

    return c * r


def calculate_total_distance(points):
    if len(points) == 0: return 0
    points = np.array(points)
    lat1, lon1 = points[:-1].T
    lat2, lon2 = points[1:].T
    distances = haversine(lat1, lon1, lat2, lon2)
    return np.round(distances.sum(), 2)

def nearest_neighbor(points):
    if len(points) == 0: 
        return []
    start = points[0]
    path = [start]
    visited = set(path)
    current = start

    while len(visited) < len(points):
        g = [p for p in points if p not in visited]
        if len(g) == 0: break
        next_point = min(g, key=lambda p: haversine(current[0], current[1], p[0], p[1]))
        path.append(next_point)
        visited.add(next_point)
        current = next_point

    path.append(start)  # return to start
    return path

def day_month_iterator():
    for month in month_iterator():
        for day in day_iterator():
            yield day, month

def month_iterator():
    for month in range(1, 13):
        yield month

def day_iterator():
    for day in range(1, 32):
        yield day

def parseBarcode(img_file_buffer):
    if img_file_buffer is None: 
        return None
    from pyzbar.pyzbar import decode
    codes = decode(Image.open(img_file_buffer))
    if len(codes) != 1: 
        return None
    code = str(codes[0].data, 'utf-8')
    # code = '164:03-06'
    courier_id, date = [x for x in code.split(':')] if ':' in code else (None, '')
    day, month = [x for x in date.split('-')] if '-' in date else (None, None)
    print((courier_id, day, month))
    return (int(courier_id) if courier_id else None), (day if day else None), (month if month else None)


def get_csv(url: str):
    return StringIO(requests.get(url).text)


def to_datetime(series: pd.Series):
    return pd.to_datetime(series, format='%m-%d %H:%M:%S')

def multimask(df: pd.DataFrame, *mask):
    mask = [x for x in mask if x is not None]
    return reduce(lambda df, mask: df[mask], mask, df)

def flat_map(f, xs): 
    return [y for ys in xs for y in f(ys)]

def horizontal(*funcs):
    for col, func in zip(st.columns(len(funcs)), funcs):
        with col:
            if func:
                func()

def write_empty(message: str):
    st.write(f"""
    ### Wow, such empty! 🙂
    {message}
    """)