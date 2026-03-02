"""Restore remaining regions with missing geometry via Overpass alternate server."""
import sys, os, json, time, requests
from uuid import uuid4
os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

def get_osm_relations(region_name, server_idx=0):
    query = f"""
[out:json][timeout:120];
area["name"="{region_name}"]["admin_level"="4"]->.region;
relation["boundary"="administrative"]["admin_level"="6"](area.region);
out tags;
"""
    server = SERVERS[server_idx % len(SERVERS)]
    try:
        resp = requests.post(server, data={'data': query}, timeout=150)
        if resp.status_code == 200:
            data = resp.json()
            result = []
            for el in data.get('elements', []):
                tags = el.get('tags', {})
                name = tags.get('name', '')
                osm_id = el.get('id')
                if name and osm_id:
                    result.append({'osm_id': osm_id, 'name': name})
            return result
    except Exception as e:
        print(f"    Error ({server}): {e}")
    return None


def download_polygon(osm_id):
    url = "https://nominatim.openstreetmap.org/lookup"
    params = {'osm_ids': f'R{osm_id}', 'format': 'json', 'polygon_geojson': 1}
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                geojson = data[0].get('geojson')
                if geojson and geojson.get('type') in ('Polygon', 'MultiPolygon'):
                    return geojson
    except:
        pass
    return None


def main():
    # Find regions still needing geometry
    with ENGINE.connect() as conn:
        damaged = conn.execute(text("""
            SELECT r.id, r.name, COUNT(d.id), COUNT(d.geom)
            FROM regions r LEFT JOIN districts d ON d.region_id = r.id
            GROUP BY r.id, r.name
            HAVING COUNT(d.id) > 0 AND COUNT(d.geom) < COUNT(d.id)
            ORDER BY r.name
        """)).fetchall()
    
    print(f"Regions needing geometry: {len(damaged)}")
    for rid, rname, cnt, gcnt in damaged:
        print(f"  {rname}: {gcnt}/{cnt}")
    
    for rid, rname, cnt, gcnt in damaged:
        print(f"\n{rname}")
        region_id = str(rid)
        
        # Try both servers
        relations = None
        for si in range(len(SERVERS)):
            relations = get_osm_relations(rname, si)
            if relations:
                break
            time.sleep(5)
        
        if not relations:
            print(f"    FAILED on all servers")
            continue
        
        print(f"    Found {len(relations)} in OSM")
        
        # Clear and reload
        with ENGINE.connect() as conn:
            conn.execute(text("DELETE FROM districts WHERE region_id = :rid"), {"rid": region_id})
            conn.commit()
        
        inserted = 0
        for rel in relations:
            geojson = download_polygon(rel['osm_id'])
            if geojson:
                try:
                    with ENGINE.connect() as conn:
                        conn.execute(text("""
                            INSERT INTO districts (id, region_id, name, geom, geom_simplified, created_at)
                            VALUES (:id, :rid, :name,
                                    ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                                    ST_SimplifyPreserveTopology(
                                        ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))), 0.005),
                                    NOW())
                        """), {
                            'id': str(uuid4()), 'rid': region_id,
                            'name': rel['name'], 'geojson': json.dumps(geojson),
                        })
                        conn.commit()
                    inserted += 1
                except:
                    pass
            time.sleep(1.1)
        
        print(f"    Loaded: {inserted}/{len(relations)}")
        time.sleep(3)
    
    # Final check
    print(f"\n{'='*60}")
    with ENGINE.connect() as conn:
        stats = conn.execute(text("""
            SELECT COUNT(d.id), COUNT(d.geom) FROM districts d
        """)).fetchone()
    print(f"Total: {stats[0]} districts, {stats[1]} with geometry")
    
    with ENGINE.connect() as conn:
        still = conn.execute(text("""
            SELECT r.name, COUNT(d.id), COUNT(d.geom)
            FROM regions r LEFT JOIN districts d ON d.region_id = r.id
            GROUP BY r.name
            HAVING COUNT(d.geom) < COUNT(d.id) AND COUNT(d.id) > 0
        """)).fetchall()
    if still:
        print("Still missing:")
        for n, c, g in still:
            print(f"  {n}: {g}/{c}")
    else:
        print("All regions have 100% geometry!")


if __name__ == "__main__":
    main()
