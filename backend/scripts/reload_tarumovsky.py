# -*- coding: utf-8 -*-
"""Перезагрузить Тарумовский район из Overpass."""
import sys
import io
import json
import time
import urllib.request
import urllib.parse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
REGION = "Республика Дагестан"
NAME = "Тарумовский муниципальный район"

def overpass_query(q):
    for url in ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]:
        try:
            data = urllib.parse.urlencode({"data": q}).encode()
            req = urllib.request.Request(url, data=data, headers={"User-Agent": "ZoneMonitoring/1.0"})
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            print(f"  {url}: {e}")
    raise RuntimeError("Overpass failed")

def nominatim_lookup(osm_id):
    url = f"https://nominatim.openstreetmap.org/lookup?osm_ids=R{osm_id}&format=json&polygon_geojson=1"
    req = urllib.request.Request(url, headers={"User-Agent": "ZoneMonitoring/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
        return data[0] if data else None

def main():
    q = '[out:json][timeout:60];area["ISO3166-2"="RU-DA"]->.d;(relation["boundary"="administrative"]["admin_level"="6"](area.d););out tags;'
    result = overpass_query(q)
    osm_id = None
    for el in result.get("elements", []):
        n = (el.get("tags", {}).get("name") or "").lower()
        if "тарумов" in n:
            osm_id = el["id"]
            break
    if not osm_id:
        print("Tarumovsky not found in Overpass")
        return
    print(f"Found R{osm_id}")
    time.sleep(1.1)
    d = nominatim_lookup(osm_id)
    if not d or not d.get("geojson"):
        print("No geometry")
        return
    gj = d["geojson"]
    if gj.get("type") not in ("Polygon", "MultiPolygon"):
        print("Invalid type")
        return
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE districts d SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)))
            FROM regions r WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
        """), {"g": json.dumps(gj), "region": REGION, "name": NAME})
    a = engine.connect().execute(text("""
        SELECT ROUND((ST_Area(d.geom::geography)/1000000)::numeric, 1)
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = :region AND d.name = :name
    """), {"region": REGION, "name": NAME}).scalar()
    h = engine.connect().execute(text("""
        SELECT COALESCE(SUM(ST_NumInteriorRings(g.geom)), 0)
        FROM districts d JOIN regions r ON d.region_id = r.id,
        LATERAL ST_Dump(d.geom) AS g WHERE r.name = :region AND d.name = :name
    """), {"region": REGION, "name": NAME}).scalar()
    print(f"OK: {a} km2, {h} holes")

if __name__ == "__main__":
    main()
