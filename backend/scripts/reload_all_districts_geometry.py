"""Reload ALL district geometries with proper region context."""
import sys
import time
import json
import requests
from sqlalchemy import create_engine, text

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from app.core.config import settings


def get_engine():
    return create_engine(settings.DATABASE_URL)


def search_nominatim_with_region(district_name, region_name):
    """Search Nominatim with region context for better accuracy."""
    clean_district = district_name.replace('муниципальный район', '').replace('городской округ', '').strip()
    clean_region = region_name
    
    # Try multiple search strategies
    queries = [
        f"{clean_district} район, {clean_region}, Россия",
        f"{clean_district}, {clean_region}, Россия",
        f"{district_name}, {clean_region}",
    ]
    
    headers = {'User-Agent': 'ZoneMonitoring/1.0 (geometry reload)'}
    
    for query in queries:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': query,
            'format': 'json',
            'polygon_geojson': 1,
            'limit': 5,
        }
        
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            if resp.status_code == 200:
                results = resp.json()
                
                # Find best polygon result
                for r in results:
                    geojson = r.get('geojson')
                    if geojson and geojson.get('type') in ('Polygon', 'MultiPolygon'):
                        # Verify it's in the right region by checking display_name
                        display = r.get('display_name', '').lower()
                        region_lower = region_name.lower()
                        # Check if region name appears in result
                        region_words = region_lower.replace('область', '').replace('край', '').replace('республика', '').strip().split()
                        if any(word in display for word in region_words if len(word) > 3):
                            return geojson
                
                # If no region match, still return first polygon if available
                for r in results:
                    geojson = r.get('geojson')
                    if geojson and geojson.get('type') in ('Polygon', 'MultiPolygon'):
                        return geojson
        except Exception as e:
            print(f"      Error: {e}")
        
        time.sleep(1.1)  # Rate limit
    
    return None


def update_district_geometry(district_id, geojson):
    """Update district geometry in database."""
    engine = get_engine()
    geojson_str = json.dumps(geojson)
    
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE districts
            SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                geom_simplified = ST_SimplifyPreserveTopology(
                    ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                    0.01
                )
            WHERE id = :id
        """), {'geojson': geojson_str, 'id': str(district_id)})
        conn.commit()


def main():
    print("=" * 60)
    print("Перезагрузка ВСЕХ геометрий районов с учётом региона")
    print("=" * 60)
    
    engine = get_engine()
    
    # Get all districts
    with engine.connect() as conn:
        districts = conn.execute(text("""
            SELECT d.id, d.name, r.name as region_name
            FROM districts d
            JOIN regions r ON d.region_id = r.id
            ORDER BY r.name, d.name
        """)).fetchall()
    
    print(f"Всего районов: {len(districts)}\n")
    
    updated = 0
    failed = []
    
    for i, (d_id, d_name, r_name) in enumerate(districts):
        pct = (i + 1) * 100 // len(districts)
        print(f"[{i+1}/{len(districts)} {pct}%] {r_name} -> {d_name[:40]}...", end=" ", flush=True)
        
        geojson = search_nominatim_with_region(d_name, r_name)
        
        if geojson:
            try:
                update_district_geometry(d_id, geojson)
                print("OK")
                updated += 1
            except Exception as e:
                print(f"DB error: {str(e)[:50]}")
                failed.append((r_name, d_name))
        else:
            print("not found")
            failed.append((r_name, d_name))
        
        # Progress save every 100
        if (i + 1) % 100 == 0:
            print(f"\n--- Progress: {updated} updated, {len(failed)} failed ---\n")
    
    print("\n" + "=" * 60)
    print(f"РЕЗУЛЬТАТ: Обновлено {updated} из {len(districts)}")
    print(f"Не найдено: {len(failed)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
