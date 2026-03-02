"""
2-step process:
  Step 1: Restore geometry from OSM for damaged regions (Overpass + Nominatim by ID)
  Step 2: Rename ALL regions' districts to official ОКТМО names (names only, no delete/add)
"""
import sys
import os
import re
import json
import time
import requests
from uuid import uuid4
from bs4 import BeautifulSoup

os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

# ========== OSM FUNCTIONS ==========

def get_osm_relations(region_name):
    osm_name = region_name
    query = f"""
[out:json][timeout:120];
area["name"="{osm_name}"]["admin_level"="4"]->.region;
relation["boundary"="administrative"]["admin_level"="6"](area.region);
out tags;
"""
    try:
        resp = requests.post("https://overpass-api.de/api/interpreter",
                           data={'data': query}, timeout=150)
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
        print(f"    Overpass error: {e}")
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


def restore_from_osm(region_name, region_id):
    """Full reload from OSM for a region."""
    relations = get_osm_relations(region_name)
    if not relations:
        print(f"    Overpass failed!")
        return False
    
    print(f"    Found {len(relations)} in OSM")
    
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
    return True


# ========== ОКТМО FUNCTIONS ==========

OKTMO_TO_REGION = {
    "01": "Алтайский край", "03": "Краснодарский край", "04": "Красноярский край",
    "05": "Приморский край", "07": "Ставропольский край", "08": "Хабаровский край",
    "10": "Амурская область", "11": "Архангельская область", "12": "Астраханская область",
    "14": "Белгородская область", "15": "Брянская область", "17": "Владимирская область",
    "18": "Волгоградская область", "19": "Вологодская область", "20": "Воронежская область",
    "22": "Нижегородская область", "24": "Ивановская область", "25": "Иркутская область",
    "26": "Республика Ингушетия", "27": "Калининградская область", "28": "Тверская область",
    "29": "Калужская область", "30": "Камчатский край", "32": "Кемеровская область",
    "33": "Кировская область", "34": "Костромская область", "35": "Республика Крым",
    "36": "Самарская область", "37": "Курганская область", "38": "Курская область",
    "40": "город Санкт-Петербург", "41": "Ленинградская область", "42": "Липецкая область",
    "44": "Магаданская область", "45": "город Москва", "46": "Московская область",
    "47": "Мурманская область", "49": "Новгородская область", "50": "Новосибирская область",
    "52": "Омская область", "53": "Оренбургская область", "54": "Орловская область",
    "56": "Пензенская область", "57": "Пермский край", "58": "Псковская область",
    "60": "Ростовская область", "61": "Рязанская область", "63": "Саратовская область",
    "64": "Сахалинская область", "65": "Свердловская область", "66": "Смоленская область",
    "67": "город Севастополь", "68": "Тамбовская область", "69": "Томская область",
    "70": "Тульская область", "71": "Тюменская область", "73": "Ульяновская область",
    "75": "Челябинская область", "76": "Забайкальский край", "77": "Чукотский автономный округ",
    "78": "Ярославская область", "79": "Республика Адыгея", "80": "Республика Башкортостан",
    "81": "Республика Бурятия", "82": "Республика Дагестан",
    "83": "Кабардино-Балкарская Республика", "84": "Республика Алтай",
    "85": "Республика Калмыкия", "86": "Республика Карелия", "87": "Республика Коми",
    "88": "Республика Марий Эл", "89": "Республика Мордовия",
    "90": "Республика Северная Осетия - Алания", "91": "Карачаево-Черкесская Республика",
    "92": "Республика Татарстан", "93": "Республика Тыва", "94": "Удмуртская Республика",
    "95": "Республика Хакасия", "96": "Чеченская Республика", "97": "Чувашская Республика",
    "98": "Республика Саха (Якутия)", "99": "Еврейская автономная область",
}

REGION_TO_OKTMO = {v: k for k, v in OKTMO_TO_REGION.items()}

# Regions NOT in ОКТМО (skip for renaming)
NO_OKTMO = {
    "Донецкая Народная Республика", "Луганская Народная Республика",
    "Запорожская область", "Херсонская область",
    "Ненецкий автономный округ", "Ханты-Мансийский автономный округ - Югра",
    "Ямало-Ненецкий автономный округ",
}

# Exclude autonomous okrug entries from parent region ОКТМО page
OKTMO_EXCLUDES = {
    "Архангельская область": "118",  # Exclude Ненецкий АО (codes starting with 118)
    "Тюменская область": ("711", "7114"),  # Exclude ХМАО and ЯНАО
}


def fetch_oktmo_names(code, exclude_prefix=None):
    """Fetch district names from ОКТМО page."""
    url = f"https://okp-okpd.ru/oktmo.aspx?kod={code}"
    resp = requests.get(url, timeout=30)
    resp.encoding = 'windows-1251'
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    names = []
    for tr in soup.find_all('tr'):
        cells = tr.find_all('td')
        if len(cells) >= 2:
            code_text = cells[0].get_text(strip=True)
            name_text = cells[1].get_text(strip=True)
            if re.match(r'^\d{11}$', code_text):
                if exclude_prefix:
                    if isinstance(exclude_prefix, tuple):
                        if any(code_text.startswith(p) for p in exclude_prefix):
                            continue
                    elif code_text.startswith(exclude_prefix):
                        continue
                names.append(name_text)
    return names


def normalize(name):
    """Normalize for matching."""
    n = name.strip().lower()
    for w in ['муниципальный район', 'муниципальный округ', 'городской округ',
              'район', 'округ', 'городской', 'город', 'зато', 'муниципальный',
              'внутригородское муниципальное образование',
              'внутригородской муниципальный округ',
              'муниципальное образование']:
        n = n.replace(w, '')
    n = n.replace('ё', 'е').replace('-', '').replace(' ', '').replace('«', '').replace('»', '')
    return n


def transform_name(name):
    """Transform 'город X' -> 'городской округ X'."""
    if 'внутригородское' in name.lower() or 'внутригородской' in name.lower():
        return name
    if 'поселение' in name.lower():
        return name
    m = re.match(r'^город\s+(.+)$', name)
    if m:
        return f"городской округ {m.group(1)}"
    return name


def rename_region(region_name, region_id, oktmo_code):
    """Rename-only: match ОКТМО names to existing DB entries, rename."""
    exclude = OKTMO_EXCLUDES.get(region_name)
    oktmo_names_raw = fetch_oktmo_names(oktmo_code, exclude)
    oktmo_names = [transform_name(n) for n in oktmo_names_raw]
    
    with ENGINE.connect() as conn:
        rows = conn.execute(text(
            "SELECT id, name FROM districts WHERE region_id = :rid ORDER BY name"
        ), {"rid": region_id}).fetchall()
    
    db_by_norm = {}
    for did, dname in rows:
        norm = normalize(dname)
        db_by_norm[norm] = (str(did), dname)
    
    renames = 0
    matched = 0
    unmatched_oktmo = []
    
    for target in oktmo_names:
        target_norm = normalize(target)
        if target_norm in db_by_norm:
            did, dname = db_by_norm[target_norm]
            if dname != target:
                with ENGINE.connect() as conn:
                    conn.execute(text("UPDATE districts SET name = :name WHERE id = :id"),
                               {"name": target, "id": did})
                    conn.commit()
                renames += 1
            else:
                matched += 1
        else:
            unmatched_oktmo.append(target)
    
    if renames or unmatched_oktmo:
        print(f"    Renamed: {renames}, Already OK: {matched}, ОКТМО not matched: {len(unmatched_oktmo)}")
        if unmatched_oktmo and len(unmatched_oktmo) <= 5:
            for name in unmatched_oktmo:
                print(f"      ? {name}")
    else:
        print(f"    All {matched} names OK")
    
    return renames


def main():
    # Get all regions from DB
    with ENGINE.connect() as conn:
        all_regions = conn.execute(text(
            "SELECT id, name FROM regions ORDER BY name"
        )).fetchall()
    all_regions = [(str(r[0]), r[1]) for r in all_regions]
    
    # === STEP 1: Restore damaged regions from OSM ===
    print("=" * 70)
    print("STEP 1: Restore damaged regions (missing geometry)")
    print("=" * 70)
    
    with ENGINE.connect() as conn:
        damaged = conn.execute(text("""
            SELECT r.id, r.name, COUNT(d.id), COUNT(d.geom)
            FROM regions r LEFT JOIN districts d ON d.region_id = r.id
            GROUP BY r.id, r.name
            HAVING COUNT(d.id) > 0 AND COUNT(d.geom) < COUNT(d.id)
            ORDER BY r.name
        """)).fetchall()
    
    if damaged:
        print(f"\nDamaged regions: {len(damaged)}")
        for rid, rname, cnt, gcnt in damaged:
            print(f"  {rname}: {gcnt}/{cnt} with geometry")
        
        for rid, rname, cnt, gcnt in damaged:
            print(f"\nRestoring: {rname}")
            restore_from_osm(rname, str(rid))
            time.sleep(3)
    else:
        print("\nNo damaged regions!")
    
    # === STEP 2: Rename all districts to ОКТМО names ===
    print(f"\n{'='*70}")
    print("STEP 2: Rename districts to official ОКТМО names")
    print(f"{'='*70}")
    
    total_renames = 0
    for region_id, region_name in all_regions:
        if region_name in NO_OKTMO:
            continue
        
        oktmo_code = REGION_TO_OKTMO.get(region_name)
        if not oktmo_code:
            continue
        
        print(f"\n{region_name} (ОКТМО={oktmo_code})")
        renames = rename_region(region_name, region_id, oktmo_code)
        total_renames += renames
        time.sleep(0.5)
    
    print(f"\n{'='*70}")
    print(f"TOTAL renames: {total_renames}")
    
    # Final stats
    with ENGINE.connect() as conn:
        stats = conn.execute(text("""
            SELECT r.name, COUNT(d.id), COUNT(d.geom)
            FROM regions r LEFT JOIN districts d ON d.region_id = r.id
            GROUP BY r.name ORDER BY COUNT(d.id)
        """)).fetchall()
    
    total_d = total_g = 0
    for name, cnt, gcnt in stats:
        total_d += cnt
        total_g += gcnt
    print(f"\nFinal: {total_d} districts, {total_g} with geometry")
    
    no_geom = [(n, c, g) for n, c, g in stats if g < c and c > 0]
    if no_geom:
        print(f"\nStill missing geometry:")
        for name, cnt, gcnt in no_geom:
            print(f"  {name}: {gcnt}/{cnt}")


if __name__ == "__main__":
    main()
