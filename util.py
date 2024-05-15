from io import StringIO
import numpy as np
import folium as f
from PIL import Image
import requests


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
    start = points[0]
    path = [start]
    visited = set()
    visited.add(start)
    current = start

    while len(visited) < len(points):
        next_point = min((p for p in points if p not in visited), key=lambda p: haversine(current[0], current[1], p[0], p[1]))
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


def drawRoute(coords):
    coords = np.array(coords)
    m = f.Map(location=coords.mean(axis=0), zoom_start=13)

    f.PolyLine(coords, color="blue", weight=2.5, opacity=1).add_to(m)
    for x, y in coords:
        f.Circle((x, y), 10).add_to(m)

    fileName = 'temp/map.html'
    m.save(fileName)
    with open(fileName) as file:
        return file.read()
    

def parseBarcode(img_file_buffer):
    from pyzbar.pyzbar import decode
    if img_file_buffer is None: 
        return None
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
