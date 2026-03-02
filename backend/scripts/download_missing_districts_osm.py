"""Download missing district geometries from OSM Overpass API."""
import sys
import time
import json
import requests
from sqlalchemy import create_engine, text

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from app.core.config import settings


def get_engine():
    return create_engine(settings.DATABASE_URL)


def get_missing_districts():
    """Get districts without geometry."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT d.id, d.name, r.name as region_name
            FROM districts d
            JOIN regions r ON d.region_id = r.id
            WHERE d.geom IS NULL
            ORDER BY r.name, d.name
        """)).fetchall()
    return result


def search_osm_district(district_name, region_name):
    """Search for district geometry in OSM using Nominatim."""
    # Clean names for search
    clean_district = district_name.replace('муниципальный район', '').replace('городской округ', '').strip()
    clean_region = region_name.replace('область', '').replace('край', '').replace('Республика', '').strip()
    
    # Try Nominatim search
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': f"{clean_district}, {region_name}, Россия",
        'format': 'json',
        'polygon_geojson': 1,
        'limit': 1,
        'countrycodes': 'ru'
    }
    headers = {'User-Agent': 'ZoneMonitoring/1.0'}
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data and 'geojson' in data[0]:
                return data[0]['geojson']
    except Exception as e:
        print(f"    Nominatim error: {e}")
    
    return None


def download_with_overpass(district_name, region_name):
    """Try to find district using Overpass API."""
    clean_district = district_name.replace('муниципальный район', '').replace('городской округ', '').strip()
    
    # Overpass query for administrative boundary
    query = f"""
    [out:json][timeout:60];
    area["name"="{region_name}"]["admin_level"="4"]->.region;
    (
      relation["admin_level"~"6|7|8"]["name"~"{clean_district}"](area.region);
    );
    out geom;
    """
    
    url = "https://overpass-api.de/api/interpreter"
    try:
        resp = requests.post(url, data={'data': query}, timeout=90)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('elements'):
                # Convert OSM to GeoJSON
                return osm_to_geojson(data['elements'][0])
    except Exception as e:
        print(f"    Overpass error: {e}")
    
    return None


def osm_to_geojson(element):
    """Convert OSM element to GeoJSON geometry."""
    if 'bounds' in element:
        # Create simple polygon from bounds
        bounds = element['bounds']
        coords = [[
            [bounds['minlon'], bounds['minlat']],
            [bounds['maxlon'], bounds['minlat']],
            [bounds['maxlon'], bounds['maxlat']],
            [bounds['minlon'], bounds['maxlat']],
            [bounds['minlon'], bounds['minlat']]
        ]]
        return {'type': 'Polygon', 'coordinates': coords}
    
    if 'geometry' in element:
        # Extract polygon from geometry
        coords = [[node['lon'], node['lat']] for node in element['geometry']]
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        return {'type': 'Polygon', 'coordinates': [coords]}
    
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
    print("Загрузка недостающих геометрий районов из OSM...")
    
    districts = get_missing_districts()
    print(f"Районов без геометрии: {len(districts)}")
    
    if not districts:
        print("Все районы имеют геометрию!")
        return
    
    # Group by region
    by_region = {}
    for d_id, d_name, r_name in districts:
        if r_name not in by_region:
            by_region[r_name] = []
        by_region[r_name].append((d_id, d_name))
    
    print(f"\nПо регионам:")
    for region, dists in sorted(by_region.items()):
        print(f"  {region}: {len(dists)} районов")
    
    updated = 0
    failed = []
    
    for region, dists in sorted(by_region.items()):
        print(f"\n=== {region} ===")
        
        for d_id, d_name in dists:
            print(f"  {d_name}...", end=" ", flush=True)
            
            # Try Nominatim first
            geojson = search_osm_district(d_name, region)
            
            if not geojson:
                # Try Overpass
                time.sleep(1)  # Rate limit
                geojson = download_with_overpass(d_name, region)
            
            if geojson:
                try:
                    update_district_geometry(d_id, geojson)
                    print("OK")
                    updated += 1
                except Exception as e:
                    print(f"DB error: {e}")
                    failed.append((region, d_name))
            else:
                print("не найдено")
                failed.append((region, d_name))
            
            time.sleep(1)  # Rate limit
    
    print(f"\n\nОбновлено: {updated}")
    print(f"Не найдено: {len(failed)}")
    
    if failed:
        print("\nНе удалось найти:")
        for region, name in failed:
            print(f"  {region} -> {name}")


if __name__ == "__main__":
    main()
