"""Fix DNR/LNR district names: Ukrainian -> Russian using name:ru from OSM"""
import sys, requests, time
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

REGION_IDS = {
    'Донецкая Народная Республика': 71973,
    'Луганская Народная Республика': 71971,
}

for region_name, osm_id in REGION_IDS.items():
    print(f"\n=== {region_name} ===")
    
    area_id = 3600000000 + osm_id
    query = f"""
[out:json][timeout:60];
area({area_id})->.searchArea;
(
  relation["boundary"="administrative"]["admin_level"="6"](area.searchArea);
);
out tags;
"""
    resp = requests.post("https://overpass-api.de/api/interpreter",
                        data={'data': query}, headers=HEADERS, timeout=90)
    elements = resp.json().get('elements', [])
    
    for el in elements:
        tags = el.get('tags', {})
        name_ua = tags.get('name', '')
        name_ru = tags.get('name:ru', '')
        
        if name_ru and name_ru != name_ua:
            # Add proper type
            if 'район' not in name_ru:
                name_ru = name_ru + ' район'
            
            print(f"  {name_ua} -> {name_ru}")
            
            with ENGINE.begin() as c:
                c.execute(text("""
                    UPDATE districts SET name = :new_name
                    WHERE name = :old_name
                    AND region_id = (SELECT id FROM regions WHERE name = :region)
                """), {'new_name': name_ru, 'old_name': name_ua, 'region': region_name})
        else:
            print(f"  {name_ua} (no name:ru tag)")
    
    time.sleep(3)

# Verify
with ENGINE.connect() as c:
    for region_name in REGION_IDS:
        rows = c.execute(text("""
            SELECT d.name FROM districts d
            JOIN regions r ON d.region_id = r.id
            WHERE r.name = :name ORDER BY d.name
        """), {'name': region_name}).fetchall()
        print(f"\n{region_name}:")
        for r in rows:
            print(f"  {r[0]}")

print("\nDone!")
