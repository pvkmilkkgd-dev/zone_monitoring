"""
Fix Arkhangelsk Oblast REGION geometry by re-downloading from Nominatim.
The region polygon was corrupted by previous clipping operations.
"""
import sys, os, json, requests
os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}


def main():
    # Step 1: Check current state
    print("=== Current state ===")
    with ENGINE.connect() as c:
        r = c.execute(text(
            "SELECT id, name, ST_Area(geom::geography)/1e6, "
            "ST_NPoints(geom), ST_XMin(geom), ST_YMin(geom), "
            "ST_XMax(geom), ST_YMax(geom) "
            "FROM regions WHERE name = 'Архангельская область'"
        )).fetchone()
        rid = str(r[0])
        print(f"  Area: {r[2]:.0f} km2, Points: {r[3]}")
        print(f"  Bbox: ({r[4]:.2f}, {r[5]:.2f}) - ({r[6]:.2f}, {r[7]:.2f})")
    
    # Step 2: Download fresh geometry from Nominatim
    # Arkhangelsk Oblast OSM relation ID = 140337
    print("\n=== Downloading fresh geometry from Nominatim ===")
    url = "https://nominatim.openstreetmap.org/lookup"
    params = {
        'osm_ids': 'R140337',
        'format': 'json',
        'polygon_geojson': 1,
        'polygon_threshold': 0.0,
    }
    resp = requests.get(url, params=params, headers=HEADERS, timeout=60)
    data = resp.json()
    
    if not data:
        print("ERROR: No data from Nominatim!")
        return
    
    geojson = data[0].get('geojson')
    if not geojson:
        print("ERROR: No geojson!")
        return
    
    print(f"  Type: {geojson['type']}")
    
    # Count points
    def count_pts(coords):
        total = 0
        if isinstance(coords, list) and len(coords) > 0:
            if isinstance(coords[0], (int, float)):
                return 1
            for item in coords:
                total += count_pts(item)
        return total
    
    pts = count_pts(geojson['coordinates'])
    print(f"  Points: {pts}")
    print(f"  Display: {data[0].get('display_name', '')[:80]}")
    bbox = data[0].get('boundingbox', [])
    print(f"  Bbox: {bbox}")
    
    # Step 3: Update region geometry
    print("\n=== Updating region geometry ===")
    with ENGINE.connect() as c:
        c.execute(text("""
            UPDATE regions SET
                geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                geom_simplified = ST_SimplifyPreserveTopology(
                    ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))), 0.01)
            WHERE id = :rid
        """), {"geojson": json.dumps(geojson), "rid": rid})
        c.commit()
    
    # Verify
    with ENGINE.connect() as c:
        r2 = c.execute(text(
            "SELECT ST_Area(geom::geography)/1e6, ST_NPoints(geom), "
            "ST_XMin(geom), ST_YMin(geom), ST_XMax(geom), ST_YMax(geom) "
            "FROM regions WHERE id = :rid"
        ), {"rid": rid}).fetchone()
        print(f"  New area: {r2[0]:.0f} km2, Points: {r2[1]}")
        print(f"  New bbox: ({r2[2]:.2f}, {r2[3]:.2f}) - ({r2[4]:.2f}, {r2[5]:.2f})")
    
    # Step 4: Re-clip districts to the new region boundary
    print("\n=== Re-clipping districts to new region boundary ===")
    with ENGINE.connect() as c:
        # First check current district coverage
        before = c.execute(text("""
            SELECT SUM(ST_Area(d.geom::geography)/1e6)
            FROM districts d WHERE d.region_id = :rid AND d.geom IS NOT NULL
        """), {"rid": rid}).fetchone()[0]
        print(f"  District area before re-clip: {before:.0f} km2")
    
    # Re-download and reload all districts fresh for this region
    # Actually, just re-clip existing districts to the new region boundary
    with ENGINE.connect() as c:
        c.execute(text("""
            UPDATE districts d SET
                geom = ST_Multi(ST_MakeValid(
                    ST_Intersection(d.geom, r.geom)
                )),
                geom_simplified = ST_SimplifyPreserveTopology(
                    ST_Multi(ST_MakeValid(
                        ST_Intersection(d.geom, r.geom)
                    )), 0.005)
            FROM regions r
            WHERE d.region_id = r.id
              AND d.region_id = :rid
              AND d.geom IS NOT NULL
        """), {"rid": rid})
        c.commit()
    
    with ENGINE.connect() as c:
        after = c.execute(text("""
            SELECT SUM(ST_Area(d.geom::geography)/1e6)
            FROM districts d WHERE d.region_id = :rid AND d.geom IS NOT NULL
        """), {"rid": rid}).fetchone()[0]
        print(f"  District area after re-clip: {after:.0f} km2")
        print(f"  Coverage: {after/r2[0]*100:.1f}%")
    
    # Show final district list
    print("\n=== Final districts ===")
    with ENGINE.connect() as c:
        rows = c.execute(text(
            "SELECT name, ST_Area(geom::geography)/1e6, ST_NPoints(geom) "
            "FROM districts WHERE region_id = :rid AND geom IS NOT NULL ORDER BY name"
        ), {"rid": rid}).fetchall()
    for name, area, npts in rows:
        print(f"  {area:>10.0f} km2  {npts:>6d} pts  {name}")
    
    print(f"\nOverall:")
    with ENGINE.connect() as c:
        stats = c.execute(text("SELECT COUNT(id), COUNT(geom) FROM districts")).fetchone()
    print(f"  {stats[0]} districts, {stats[1]} with geometry")


if __name__ == "__main__":
    main()
