"""
Fix Arkhangelsk: Investigate and fix Primorsky district oversized geometry.
Also check/fix region boundary.
"""
import sys, os, json, time, requests
from uuid import uuid4

os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}


def main():
    with ENGINE.connect() as c:
        rid = str(c.execute(text(
            "SELECT id FROM regions WHERE name = 'Архангельская область'"
        )).fetchone()[0])
    
    # Check Приморский район details
    print("=== Приморский муниципальный район ===")
    with ENGINE.connect() as c:
        pr = c.execute(text(
            "SELECT name, "
            "ST_Area(geom::geography)/1e6, "
            "ST_AsText(ST_Centroid(geom)), "
            "ST_XMin(geom), ST_YMin(geom), ST_XMax(geom), ST_YMax(geom), "
            "ST_NPoints(geom) "
            "FROM districts WHERE region_id = :rid AND name LIKE '%Приморск%'"
        ), {"rid": rid}).fetchone()
    
    print(f"Area: {pr[1]:.0f} km2")
    print(f"Centroid: {pr[2]}")
    print(f"Bbox: ({pr[3]:.2f}, {pr[4]:.2f}) - ({pr[5]:.2f}, {pr[6]:.2f})")
    print(f"Points: {pr[7]}")
    
    # Check Новая Земля
    print("\n=== Новая Земля ===")
    with ENGINE.connect() as c:
        nz = c.execute(text(
            "SELECT name, "
            "ST_Area(geom::geography)/1e6, "
            "ST_AsText(ST_Centroid(geom)), "
            "ST_XMin(geom), ST_YMin(geom), ST_XMax(geom), ST_YMax(geom) "
            "FROM districts WHERE region_id = :rid AND name LIKE '%Новая Земля%'"
        ), {"rid": rid}).fetchone()
    
    print(f"Area: {nz[1]:.0f} km2")
    print(f"Centroid: {nz[2]}")
    print(f"Bbox: ({nz[3]:.2f}, {nz[4]:.2f}) - ({nz[5]:.2f}, {nz[6]:.2f})")
    
    # Check region bbox
    print("\n=== Region ===")
    with ENGINE.connect() as c:
        rg = c.execute(text(
            "SELECT ST_Area(geom::geography)/1e6, "
            "ST_AsText(ST_Centroid(geom)), "
            "ST_XMin(geom), ST_YMin(geom), ST_XMax(geom), ST_YMax(geom) "
            "FROM regions WHERE id = :rid"
        ), {"rid": rid}).fetchone()
    
    print(f"Area: {rg[0]:.0f} km2")
    print(f"Centroid: {rg[1]}")
    print(f"Bbox: ({rg[2]:.2f}, {rg[3]:.2f}) - ({rg[4]:.2f}, {rg[5]:.2f})")
    
    # The Primorsky district in OSM likely includes Franz Josef Land
    # Let's check what Nominatim returns for the region
    print("\n=== Checking Nominatim for region polygon ===")
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': 'Архангельская область, Россия',
        'format': 'json',
        'limit': 3,
    }
    resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
    for r in resp.json():
        if r['osm_type'] == 'relation':
            print(f"Region OSM: R{r['osm_id']} bbox: {r.get('boundingbox', '')}")
            break
    
    time.sleep(1.1)
    
    # Check Приморский in OSM - what's the correct boundary?
    print("\n=== Searching Nominatim for Приморский район ===")
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': 'Приморский муниципальный округ, Архангельская область',
        'format': 'json',
        'polygon_geojson': 0,
        'limit': 5,
    }
    resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
    for r in resp.json():
        print(f"  {r.get('osm_type','')}{r.get('osm_id','')} "
              f"class={r.get('class','')}/{r.get('type','')} "
              f"bbox={r.get('boundingbox','')} "
              f"{r.get('display_name','')[:60]}")
    
    time.sleep(1.1)
    
    # Check what OSM relation R1330718 actually contains
    print("\n=== OSM R1330718 (Приморский) details via Nominatim ===")
    url = "https://nominatim.openstreetmap.org/lookup"
    params = {'osm_ids': 'R1330718', 'format': 'json'}
    resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
    if resp.status_code == 200:
        data = resp.json()
        if data:
            r = data[0]
            print(f"  Name: {r.get('display_name','')}")
            print(f"  Bbox: {r.get('boundingbox','')}")
            print(f"  Class: {r.get('class','')}/{r.get('type','')}")
    
    time.sleep(1.1)
    
    # Now check if there's a separate relation for Земля Франца-Иосифа
    print("\n=== Searching for Земля Франца-Иосифа ===")
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': 'Земля Франца-Иосифа',
        'format': 'json',
        'limit': 5,
    }
    resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
    for r in resp.json():
        print(f"  {r.get('osm_type','')}{r.get('osm_id','')} "
              f"class={r.get('class','')}/{r.get('type','')} "
              f"bbox={r.get('boundingbox','')} "
              f"{r.get('display_name','')[:60]}")
    
    # Update region geometry from Nominatim (might have more complete boundary)
    print("\n=== Updating region geometry ===")
    url = "https://nominatim.openstreetmap.org/lookup"
    params = {'osm_ids': 'R140337', 'format': 'json', 'polygon_geojson': 1}
    resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
    if resp.status_code == 200:
        data = resp.json()
        if data:
            geojson = data[0].get('geojson')
            if geojson and geojson.get('type') in ('Polygon', 'MultiPolygon'):
                with ENGINE.connect() as c:
                    c.execute(text("""
                        UPDATE regions SET
                            geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                            geom_simplified = ST_SimplifyPreserveTopology(
                                ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))), 0.01)
                        WHERE id = :rid
                    """), {"geojson": json.dumps(geojson), "rid": rid})
                    c.commit()
                
                with ENGINE.connect() as c:
                    new_area = c.execute(text(
                        "SELECT ST_Area(geom::geography)/1e6 FROM regions WHERE id = :rid"
                    ), {"rid": rid}).fetchone()[0]
                print(f"Updated region area: {new_area:.0f} km2")
    
    time.sleep(1.1)
    
    # Final stats
    print(f"\n{'='*60}")
    with ENGINE.connect() as c:
        rows = c.execute(text(
            "SELECT name, ST_Area(geom::geography)/1e6, "
            "ST_AsText(ST_Centroid(geom)) "
            "FROM districts WHERE region_id = :rid ORDER BY name"
        ), {"rid": rid}).fetchall()
        total = sum(r[1] for r in rows)
        rarea = c.execute(text(
            "SELECT ST_Area(geom::geography)/1e6 FROM regions WHERE id = :rid"
        ), {"rid": rid}).fetchone()[0]
    
    print(f"Region area: {rarea:.0f} km2")
    print(f"Districts total: {total:.0f} km2")
    print(f"Coverage: {total/rarea*100:.1f}%")


if __name__ == "__main__":
    main()
