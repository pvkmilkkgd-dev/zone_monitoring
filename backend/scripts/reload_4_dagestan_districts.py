# -*- coding: utf-8 -*-
"""Перезагрузить геометрию 4 районов Дагестана из Overpass."""
import sys
import io
import json
import time
import urllib.request
import urllib.parse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

import sqlalchemy as sa
from sqlalchemy import text
from app.core.config import settings

engine = sa.create_engine(settings.DATABASE_URL)
REGION = "Республика Дагестан"
TARGET_NAMES = [
    "Ахвахский муниципальный район",
    "Гумбетовский муниципальный район",
    "Казбековский муниципальный район",
    "Хасавюртовский муниципальный район",
]


OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

def overpass_query(query_str):
    for url in OVERPASS_URLS:
        try:
            data = urllib.parse.urlencode({"data": query_str}).encode()
            req = urllib.request.Request(url, data=data, headers={"User-Agent": "ZoneMonitoring/1.0"})
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            print(f"  Overpass {url}: {e}")
    raise RuntimeError("All Overpass servers failed")


def nominatim_lookup(osm_id):
    url = f"https://nominatim.openstreetmap.org/lookup?osm_ids=R{osm_id}&format=json&polygon_geojson=1"
    req = urllib.request.Request(url, headers={"User-Agent": "ZoneMonitoring/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
        if data and len(data) > 0:
            return data[0]
    return None


def normalize(name):
    n = (name or "").lower().strip()
    for w in ["муниципальный район", "муниципальный округ", "городской округ", "район", "округ", "город", "г."]:
        n = n.replace(w, "")
    n = n.replace("-", " ").replace("ё", "е").strip()
    while "  " in n:
        n = n.replace("  ", " ")
    return n


def match_osm_to_db(osm_name, db_name):
    if normalize(osm_name) == normalize(db_name):
        return True
    return normalize(osm_name) in normalize(db_name) or normalize(db_name) in normalize(osm_name)


def main():
    print("Overpass: admin_level=6 в Дагестане")
    query = """
    [out:json][timeout:60];
    area["ISO3166-2"="RU-DA"]->.dag;
    ( relation["boundary"="administrative"]["admin_level"="6"](area.dag); );
    out tags;
    """
    result = overpass_query(query)
    elements = result.get("elements", [])

    # db_name -> [(osm_id, ...), ...] — может быть несколько OSM для одного района
    mapping = {}
    for el in elements:
        name = (el.get("tags", {}).get("name") or el.get("tags", {}).get("name:ru") or "")
        for db_name in TARGET_NAMES:
            if match_osm_to_db(name, db_name):
                mapping.setdefault(db_name, []).append(el["id"])
                break

    print(f"Найдено {sum(len(v) for v in mapping.values())} relations для 4 районов")

    print("\nЗагрузка геометрий (при дублях берём с большей площадью)...")
    with engine.begin() as conn:
        for db_name, osm_ids in mapping.items():
            best_geojson = None
            best_area = 0
            for osm_id in osm_ids:
                time.sleep(1.1)
                try:
                    data = nominatim_lookup(osm_id)
                except Exception as e:
                    print(f"  FAIL R{osm_id}: {e}")
                    continue
                if not data or not data.get("geojson"):
                    continue
                geojson = data["geojson"]
                if geojson.get("type") not in ("Polygon", "MultiPolygon"):
                    continue
                # Примерная площадь для выбора большей геометрии при дублях
                def flatten_coords(c, points=None):
                    if points is None:
                        points = []
                    if isinstance(c[0], (int, float)):
                        points.append(c)
                    else:
                        for p in c:
                            flatten_coords(p, points)
                    return points
                pts = flatten_coords(geojson.get("coordinates", []))
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                area = (max(xs)-min(xs)) * (max(ys)-min(ys)) if pts else 0
                if area > best_area:
                    best_area = area
                    best_geojson = geojson
            if best_geojson:
                conn.execute(text("""
                    UPDATE districts d SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326)))
                    FROM regions r
                    WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
                """), {"gj": json.dumps(best_geojson), "region": REGION, "name": db_name})
                print(f"  OK {db_name} ({best_area:.0f})")

    print("\nГотово.")


if __name__ == "__main__":
    main()
