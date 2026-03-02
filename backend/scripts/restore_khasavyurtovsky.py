# -*- coding: utf-8 -*-
"""Восстановить Хасавюртовский район из Nominatim (OSM R1858759 — основной)."""
import sys
import io
import json
import urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

# R1858759 — Хасавюртовский муниципальный район (основной, ~1300 км²)
# R1858774 — возможно городской округ Хасавюрт (~38 км²)
OSM_IDS = [1858759, 1858774]

def nominatim_lookup(osm_id):
    url = f"https://nominatim.openstreetmap.org/lookup?osm_ids=R{osm_id}&format=json&polygon_geojson=1"
    req = urllib.request.Request(url, headers={"User-Agent": "ZoneMonitoring/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
        if data and len(data) > 0:
            return data[0]
    return None

engine = create_engine(settings.DATABASE_URL)
best = None
best_area = 0
for osm_id in OSM_IDS:
    data = nominatim_lookup(osm_id)
    if not data or not data.get("geojson"):
        continue
    geojson = data["geojson"]
    if geojson.get("type") not in ("Polygon", "MultiPolygon"):
        continue
    # Площадь через БД
    with engine.connect() as conn:
        area = conn.execute(text("""
            SELECT ST_Area(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326)::geography)/1000000
        """), {"gj": json.dumps(geojson)}).scalar()
    if area and area > best_area:
        best_area = area
        best = geojson

if best:
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE districts d SET
                geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326))),
                geom_simplified = ST_SimplifyPreserveTopology(ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326))), 0.005)
            FROM regions r
            WHERE d.region_id = r.id AND r.name = 'Республика Дагестан' AND d.name = 'Хасавюртовский муниципальный район'
        """), {"gj": json.dumps(best)})
    print(f"OK: Хасавюртовский восстановлен, {best_area:.0f} км²")
else:
    print("FAIL: не удалось загрузить геометрию")
