"""Test bounding box calculation with antimeridian fix."""
import sys
sys.path.insert(0, '.')
from sqlalchemy import create_engine, text
from app.core.config import settings
import json

engine = create_engine(settings.DATABASE_URL)

min_x = float('inf')
max_x = float('-inf')
min_y = float('inf')
max_y = float('-inf')

def process_coords(coords):
    global min_x, max_x, min_y, max_y
    if isinstance(coords[0], list):
        for c in coords:
            process_coords(c)
    else:
        lon, lat = coords[0], coords[1]
        # Apply the same fix as frontend - shift ALL negative longitudes
        if lon < 0:
            lon = lon + 360
        min_x = min(min_x, lon)
        max_x = max(max_x, lon)
        min_y = min(min_y, -lat)  # Invert lat like frontend
        max_y = max(max_y, -lat)

with engine.connect() as conn:
    # Process all regions
    result = conn.execute(text('''
        SELECT name, ST_AsGeoJSON(geom)::json as geometry
        FROM regions
        WHERE geom IS NOT NULL
    ''')).fetchall()
    
    for row in result:
        name = row[0]
        geom = row[1]
        process_coords(geom['coordinates'])
    
    print(f"Total regions: {len(result)}")
    print(f"X (lon): {min_x:.2f} to {max_x:.2f}")
    print(f"Y (-lat): {min_y:.2f} to {max_y:.2f}")
    print(f"Width: {max_x - min_x:.2f}")
    print(f"Height: {max_y - min_y:.2f}")
    print(f"Aspect ratio: {(max_x - min_x) / (max_y - min_y):.2f}")
