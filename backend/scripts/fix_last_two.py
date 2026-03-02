"""Fix last 2 Sverdlovsk districts."""
import sys, json, time, requests
from uuid import uuid4
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

def search(q):
    url = "https://nominatim.openstreetmap.org/search"
    params = {'q': q, 'format': 'json', 'polygon_geojson': 1, 'limit': 10}
    headers = {'User-Agent': 'ZoneMonitoring/1.0'}
    resp = requests.get(url, params=params, headers=headers, timeout=30)
    return resp.json() if resp.status_code == 200 else []

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    region_id = str(conn.execute(text("SELECT id FROM regions WHERE name LIKE '%Свердлов%'")).fetchone()[0])

remaining = [
    ("Сысертский район", ["Sysertsky District", "Сысертский район", "Сысерть городской округ"]),
    ("Тугулымский район", ["Tugulymsky District", "Тугулымский район", "Тугулым городской округ"]),
]

for name, queries in remaining:
    print(f"\n{name}:")
    for q in queries:
        print(f"  {q}...", end=" ", flush=True)
        results = search(q)
        for r in results:
            g = r.get('geojson')
            if g and g.get('type') in ('Polygon', 'MultiPolygon'):
                print(f"Found! ({r.get('display_name','')[:60]})")
                with engine.connect() as conn:
                    conn.execute(text("""
                        INSERT INTO districts (id, region_id, name, geom, geom_simplified, created_at)
                        VALUES (:id, :rid, :name,
                                ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                                ST_SimplifyPreserveTopology(ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))), 0.005),
                                NOW())
                    """), {'id': str(uuid4()), 'rid': region_id, 'name': name, 'geojson': json.dumps(g)})
                    conn.commit()
                print("  -> OK")
                break
        else:
            print("no polygon")
            time.sleep(1.1)
            continue
        break

with engine.connect() as conn:
    count = conn.execute(text("SELECT COUNT(*) FROM districts d JOIN regions r ON d.region_id=r.id WHERE r.name LIKE '%Свердлов%'")).scalar()
    print(f"\nTotal: {count}")
