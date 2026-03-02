"""
Load all Moscow districts (97 municipal okrugs from ОКТМО 453) with geometry from Nominatim.
Keep: городской округ Троицк, поселение Московский.
Remove: 9 administrative okrugs (ЦАО, САО, etc.).
"""
import sys
import re
import json
import time
import requests
import uuid

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
BASE = "https://classinform.ru"
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html', 'Accept-Language': 'ru-RU,ru;q=0.9'}
NOMINATIM = "https://nominatim.openstreetmap.org/search"
# Moscow bbox to bias search
MOSCOW_BBOX = "37.3,55.5,37.9,55.9"

def fetch_oktmo_453():
    from bs4 import BeautifulSoup
    url = f"{BASE}/oktmo/45300000000.html"
    time.sleep(1)
    resp = requests.get(url, headers=HEADERS, timeout=60)
    if resp.status_code != 200:
        return []
    soup = BeautifulSoup(resp.text, 'html.parser')
    lines = [l.strip() for l in soup.get_text('\n', strip=True).split('\n') if l.strip()]
    entries = []
    i = 0
    while i < len(lines):
        if re.match(r'^45[0-9]{6}$', lines[i]) and lines[i][3:6] != '000':
            if i + 1 < len(lines):
                name = re.sub(r'\s*\([^)]*\)\s*$', '', lines[i+1]).strip()
                if name and not name.startswith('Код'):
                    entries.append(name)
        i += 1
    return entries

def search_geom(name):
    """Nominatim: search district in Moscow, return GeoJSON geometry or None."""
    # "муниципальный округ Богородское" -> search "Богородское Москва"
    short = name
    for prefix in ['муниципальный округ ', 'Муниципальный округ ']:
        if short.startswith(prefix):
            short = short[len(prefix):].strip()
            break
    q = f"{short}, Москва"
    params = {
        'q': q,
        'format': 'json',
        'polygon_geojson': 1,
        'limit': 3,
        'viewbox': MOSCOW_BBOX,
        'accept-language': 'ru',
    }
    try:
        time.sleep(1.2)
        r = requests.get(NOMINATIM, params=params, headers={'User-Agent': 'ZoneMonitoring/1.0'}, timeout=30)
        if r.status_code != 200:
            return None
        results = r.json()
        for res in results:
            g = res.get('geojson')
            if not g or g.get('type') not in ('Polygon', 'MultiPolygon'):
                continue
            display = res.get('display_name', '')
            if 'Москва' not in display and 'Moscow' not in display:
                continue
            return g
    except Exception:
        pass
    return None

def main():
    print("=== 1. ОКТМО 453 ===")
    oktmo_names = fetch_oktmo_453()
    print(f"  {len(oktmo_names)} municipal okrugs")

    with ENGINE.connect() as c:
        row = c.execute(text("SELECT id FROM regions WHERE name = 'город Москва'")).fetchone()
        if not row:
            print("  Region 'город Москва' not found")
            return
        moscow_region_id = str(row[0])

    # Remove 9 AO (keep Troitsk, Moskovsky)
    ao_names = [
        'Восточный административный округ', 'Западный административный округ',
        'Северный административный округ', 'Северо-Восточный административный округ',
        'Северо-Западный административный округ', 'Центральный административный округ',
        'Юго-Восточный административный округ', 'Юго-Западный административный округ',
        'Южный административный округ'
    ]
    with ENGINE.begin() as c:
        for name in ao_names:
            c.execute(text("DELETE FROM districts WHERE region_id = :rid AND name = :name"),
                     {'rid': moscow_region_id, 'name': name})
    print("  Removed 9 AO")

    # Load geometry for each ОКТМО district and insert
    inserted = 0
    failed = []
    for i, official_name in enumerate(oktmo_names):
        geom = search_geom(official_name)
        if not geom:
            failed.append(official_name)
            continue
        geojson_str = json.dumps(geom)
        new_id = str(uuid.uuid4())
        with ENGINE.begin() as c:
            try:
                c.execute(text("""
                    INSERT INTO districts (id, region_id, name, geom)
                    VALUES (:id, :rid, :name, ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))))
                """), {'id': new_id, 'rid': moscow_region_id, 'name': official_name, 'g': geojson_str})
                inserted += 1
            except Exception as e:
                failed.append(official_name)
        if (i + 1) % 20 == 0:
            print(f"  ... {i+1}/{len(oktmo_names)} (inserted {inserted})")

    print(f"\n  Inserted: {inserted}, no geometry: {len(failed)}")
    if failed:
        print(f"  Failed (first 15): {failed[:15]}")

    with ENGINE.connect() as c:
        total = c.execute(text("SELECT COUNT(*) FROM districts WHERE region_id = :rid"), {'rid': moscow_region_id}).scalar()
        no_geom = c.execute(text("""
            SELECT COUNT(*) FROM districts WHERE region_id = :rid AND (geom IS NULL OR ST_NPoints(geom)=0)
        """), {'rid': moscow_region_id}).scalar()
    print(f"\n  Итого город Москва: {total} районов, без геометрии: {no_geom}")
    print("Done.")

if __name__ == '__main__':
    main()
