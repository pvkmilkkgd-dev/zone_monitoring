"""
Automated ОКТМО name fixing for ALL regions.
1. Scrape official ОКТМО data from okp-okpd.ru
2. Compare with DB
3. Rename/add/remove districts
4. Download geometry for new entries

Source: okp-okpd.ru/oktmo.aspx (Federal classifier ОКТМО ОК 033-2013)
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
HEADERS_NOM = {'User-Agent': 'ZoneMonitoring/1.0'}

# ОКТМО code -> DB region name mapping
OKTMO_TO_REGION = {
    "01": "Алтайский край",
    "03": "Краснодарский край",
    "04": "Красноярский край",
    "05": "Приморский край",
    "07": "Ставропольский край",
    "08": "Хабаровский край",
    "10": "Амурская область",
    "11": "Архангельская область",
    "12": "Астраханская область",
    "14": "Белгородская область",
    "15": "Брянская область",
    "17": "Владимирская область",
    "18": "Волгоградская область",
    "19": "Вологодская область",
    "20": "Воронежская область",
    "22": "Нижегородская область",
    "24": "Ивановская область",
    "25": "Иркутская область",
    "26": "Республика Ингушетия",
    "27": "Калининградская область",
    "28": "Тверская область",
    "29": "Калужская область",
    "30": "Камчатский край",
    "32": "Кемеровская область",
    "33": "Кировская область",
    "34": "Костромская область",
    "35": "Республика Крым",
    "36": "Самарская область",
    "37": "Курганская область",
    "38": "Курская область",
    "40": "город Санкт-Петербург",
    "41": "Ленинградская область",
    "42": "Липецкая область",
    "44": "Магаданская область",
    "45": "город Москва",
    "46": "Московская область",
    "47": "Мурманская область",
    "49": "Новгородская область",
    "50": "Новосибирская область",
    "52": "Омская область",
    "53": "Оренбургская область",
    "54": "Орловская область",
    "56": "Пензенская область",
    "57": "Пермский край",
    "58": "Псковская область",
    "60": "Ростовская область",
    "61": "Рязанская область",
    "63": "Саратовская область",
    "64": "Сахалинская область",
    "65": "Свердловская область",
    "66": "Смоленская область",
    "67": "город Севастополь",
    "68": "Тамбовская область",
    "69": "Томская область",
    "70": "Тульская область",
    "71": "Тюменская область",
    "73": "Ульяновская область",
    "75": "Челябинская область",
    "76": "Забайкальский край",
    "77": "Чукотский автономный округ",
    "78": "Ярославская область",
    "79": "Республика Адыгея",
    "80": "Республика Башкортостан",
    "81": "Республика Бурятия",
    "82": "Республика Дагестан",
    "83": "Кабардино-Балкарская Республика",
    "84": "Республика Алтай",
    "85": "Республика Калмыкия",
    "86": "Республика Карелия",
    "87": "Республика Коми",
    "88": "Республика Марий Эл",
    "89": "Республика Мордовия",
    "90": "Республика Северная Осетия - Алания",
    "91": "Карачаево-Черкесская Республика",
    "92": "Республика Татарстан",
    "93": "Республика Тыва",
    "94": "Удмуртская Республика",
    "95": "Республика Хакасия",
    "96": "Чеченская Республика",
    "97": "Чувашская Республика",
    "98": "Республика Саха (Якутия)",
    "99": "Еврейская автономная область",
}

# Autonomous okrugs within oblasts - use ОКТМО code prefix to filter
# Ненецкий АО is within code 11 (Архангельская), entries starting with 118..
# ХМАО is within code 71 (Тюменская), entries starting with 711..
# ЯНАО is within code 71 (Тюменская), entries starting with 7114..
AUTONOMOUS_OKRUGS = {
    "Ненецкий автономный округ": {"parent_code": "11", "prefix": "118"},
    "Ханты-Мансийский автономный округ - Югра": {"parent_code": "71", "prefix": "711"},
    "Ямало-Ненецкий автономный округ": {"parent_code": "71", "prefix": "7114"},
}

# Skip these (already done or no ОКТМО data)
SKIP_REGIONS = {
    "Алтайский край",  # Already done
    "Краснодарский край",  # Already done
    "Красноярский край",  # Already done
    "Приморский край",  # Already done
    "Ставропольский край",  # Already done
    "Хабаровский край",  # Already done
    "Амурская область",  # Already done
    "Донецкая Народная Республика",  # Not in ОКТМО
    "Луганская Народная Республика",  # Not in ОКТМО
    "Запорожская область",  # Not in ОКТМО
    "Херсонская область",  # Not in ОКТМО
}

# For autonomous okrugs, which entries belong to the parent region (not the okrug)
# Архангельская area without Ненецкий: codes NOT starting with 118
# Тюменская area without ХМАО/ЯНАО: codes NOT starting with 711 or 7114


def fetch_oktmo_page(code):
    """Fetch and parse ОКТМО page for a region code."""
    url = f"https://okp-okpd.ru/oktmo.aspx?kod={code}"
    try:
        resp = requests.get(url, timeout=30)
        resp.encoding = 'windows-1251'
        if resp.status_code != 200:
            return None
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Find the main table with districts
        districts = []
        
        # Look for table rows with ОКТМО codes
        for tr in soup.find_all('tr'):
            cells = tr.find_all('td')
            if len(cells) >= 2:
                code_text = cells[0].get_text(strip=True)
                name_text = cells[1].get_text(strip=True)
                
                # ОКТМО codes are 11 digits
                if re.match(r'^\d{11}$', code_text) and name_text:
                    districts.append({
                        'oktmo': code_text,
                        'name': name_text,
                    })
        
        return districts
    except Exception as e:
        print(f"    Fetch error: {e}")
        return None


def normalize_for_match(name):
    """Normalize name for fuzzy matching."""
    n = name.strip().lower()
    # Remove type words for comparison
    for w in ['муниципальный район', 'муниципальный округ', 'городской округ',
              'район', 'округ', 'городской', 'город', 'зато', 'муниципальный',
              'внутригородское муниципальное образование',
              'внутригородской муниципальный округ',
              'муниципальное образование', 'поселение']:
        n = n.replace(w, '')
    n = n.replace('ё', 'е').replace('-', '').replace(' ', '').replace('«', '').replace('»', '')
    return n


def transform_name(name):
    """Transform ОКТМО name to our standard format.
    'город X' -> 'городской округ X'
    """
    # Don't transform internal districts of Moscow/SPb
    if 'внутригородское' in name.lower() or 'внутригородской' in name.lower():
        return name
    if 'поселение' in name.lower():
        return name
    
    # "город X" -> "городской округ X"
    m = re.match(r'^город\s+(.+)$', name)
    if m:
        return f"городской округ {m.group(1)}"
    
    return name


def get_region_id(region_name):
    with ENGINE.connect() as conn:
        row = conn.execute(
            text("SELECT id FROM regions WHERE name = :name"),
            {"name": region_name}
        ).fetchone()
    return str(row[0]) if row else None


def get_db_districts(region_id):
    with ENGINE.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, name, geom IS NOT NULL as has_geom
            FROM districts WHERE region_id = :rid ORDER BY name
        """), {"rid": region_id}).fetchall()
    return [(str(r[0]), r[1], r[2]) for r in rows]


def download_geometry(name, region_name):
    """Download polygon geometry from Nominatim."""
    short_name = name
    # Try different search variants
    queries = [
        f"{name}, {region_name}, Россия",
        f"{name}, {region_name}",
        f"{name}, Россия",
    ]
    
    for q in queries:
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={'q': q, 'format': 'json', 'polygon_geojson': 1, 'limit': 5},
                headers=HEADERS_NOM, timeout=30
            )
            if resp.status_code == 200:
                for r in resp.json():
                    geojson = r.get('geojson')
                    if geojson and geojson.get('type') in ('Polygon', 'MultiPolygon'):
                        return geojson
        except:
            pass
        time.sleep(1.1)
    return None


def process_region(region_name, oktmo_names):
    """Process one region: compare ОКТМО names with DB, fix."""
    region_id = get_region_id(region_name)
    if not region_id:
        print(f"    Region not found in DB!")
        return {'renames': 0, 'added': 0, 'removed': 0, 'ok': 0}
    
    db_districts = get_db_districts(region_id)
    
    # Build normalized lookup for DB
    db_by_norm = {}
    for did, dname, has_geom in db_districts:
        norm = normalize_for_match(dname)
        db_by_norm[norm] = (did, dname, has_geom)
    
    # Match ОКТМО -> DB
    renames = []
    missing = []
    matched_ids = set()
    ok_count = 0
    
    for oktmo_name in oktmo_names:
        target_name = transform_name(oktmo_name)
        target_norm = normalize_for_match(target_name)
        
        if target_norm in db_by_norm:
            did, dname, has_geom = db_by_norm[target_norm]
            matched_ids.add(did)
            if dname != target_name:
                renames.append((did, dname, target_name))
            else:
                ok_count += 1
        else:
            missing.append(target_name)
    
    # Extra in DB
    extra = [(did, dname) for did, dname, _ in db_districts if did not in matched_ids]
    
    # Apply renames
    if renames:
        with ENGINE.connect() as conn:
            for did, old, new in renames:
                conn.execute(text("UPDATE districts SET name = :name WHERE id = :id"),
                           {"name": new, "id": did})
            conn.commit()
    
    # Delete extras
    if extra:
        with ENGINE.connect() as conn:
            for did, _ in extra:
                conn.execute(text("DELETE FROM districts WHERE id = :id"), {"id": did})
            conn.commit()
    
    # Add missing (with geometry)
    added_with_geom = 0
    added_no_geom = 0
    if missing:
        for name in missing:
            geojson = download_geometry(name, region_name)
            if geojson:
                geojson_str = json.dumps(geojson)
                with ENGINE.connect() as conn:
                    conn.execute(text("""
                        INSERT INTO districts (id, region_id, name, geom, geom_simplified, created_at)
                        VALUES (:id, :rid, :name,
                                ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                                ST_SimplifyPreserveTopology(
                                    ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))), 0.005),
                                NOW())
                    """), {'id': str(uuid4()), 'rid': region_id, 'name': name, 'geojson': geojson_str})
                    conn.commit()
                added_with_geom += 1
            else:
                with ENGINE.connect() as conn:
                    conn.execute(text("""
                        INSERT INTO districts (id, region_id, name, created_at)
                        VALUES (:id, :rid, :name, NOW())
                    """), {'id': str(uuid4()), 'rid': region_id, 'name': name})
                    conn.commit()
                added_no_geom += 1
            time.sleep(0.2)
    
    # Print summary
    changes = []
    if renames:
        changes.append(f"{len(renames)} renamed")
    if missing:
        changes.append(f"{added_with_geom}+{added_no_geom} added")
    if extra:
        changes.append(f"{len(extra)} removed")
    
    if changes:
        print(f"    ОКТМО: {len(oktmo_names)}, DB was: {len(db_districts)} -> Changes: {', '.join(changes)}")
        # Show renames
        for _, old, new in renames[:5]:
            print(f"      '{old}' -> '{new}'")
        if len(renames) > 5:
            print(f"      ... and {len(renames)-5} more renames")
        for name in missing[:3]:
            print(f"      + {name}")
        if len(missing) > 3:
            print(f"      ... and {len(missing)-3} more added")
        for _, name in extra[:3]:
            print(f"      - {name}")
        if len(extra) > 3:
            print(f"      ... and {len(extra)-3} more removed")
    else:
        print(f"    OK ({ok_count} names match)")
    
    return {
        'renames': len(renames),
        'added': len(missing),
        'removed': len(extra),
        'ok': ok_count,
    }


def main():
    # Collect all ОКТМО codes to process
    regions_to_process = []
    
    # Standard regions
    for code, region_name in sorted(OKTMO_TO_REGION.items()):
        if region_name in SKIP_REGIONS:
            continue
        regions_to_process.append((code, region_name, None))
    
    # Autonomous okrugs
    for ao_name, ao_config in AUTONOMOUS_OKRUGS.items():
        if ao_name in SKIP_REGIONS:
            continue
        regions_to_process.append((ao_config['parent_code'], ao_name, ao_config['prefix']))
    
    print(f"Regions to process: {len(regions_to_process)}")
    print(f"Skipping: {SKIP_REGIONS}\n")
    
    # Cache fetched pages
    page_cache = {}
    
    total_renames = 0
    total_added = 0
    total_removed = 0
    failed = []
    
    for i, (code, region_name, prefix) in enumerate(regions_to_process):
        print(f"\n[{i+1}/{len(regions_to_process)}] {region_name} (ОКТМО={code})")
        
        # Fetch ОКТМО page (with cache)
        if code not in page_cache:
            all_districts = fetch_oktmo_page(code)
            if all_districts is None:
                print(f"    FAILED to fetch ОКТМО page!")
                failed.append(region_name)
                time.sleep(2)
                continue
            page_cache[code] = all_districts
            time.sleep(1)  # Rate limit
        else:
            all_districts = page_cache[code]
        
        # Filter by prefix if needed (for autonomous okrugs and parent regions)
        if prefix:
            # This is an autonomous okrug - filter entries with this prefix
            districts = [d for d in all_districts if d['oktmo'].startswith(prefix)]
        elif region_name == "Архангельская область":
            # Exclude Ненецкий АО entries
            districts = [d for d in all_districts if not d['oktmo'].startswith("118")]
        elif region_name == "Тюменская область":
            # Exclude ХМАО and ЯНАО entries
            districts = [d for d in all_districts 
                        if not d['oktmo'].startswith("711") and not d['oktmo'].startswith("7114")]
        else:
            districts = all_districts
        
        if not districts:
            print(f"    No districts found in ОКТМО!")
            failed.append(region_name)
            continue
        
        oktmo_names = [d['name'] for d in districts]
        print(f"    ОКТМО entries: {len(oktmo_names)}")
        
        result = process_region(region_name, oktmo_names)
        total_renames += result['renames']
        total_added += result['added']
        total_removed += result['removed']
    
    # Summary
    print(f"\n{'='*70}")
    print(f"TOTAL: {total_renames} renames, {total_added} added, {total_removed} removed")
    
    if failed:
        print(f"\nFailed ({len(failed)}):")
        for name in failed:
            print(f"  - {name}")
    
    # Final stats
    with ENGINE.connect() as conn:
        stats = conn.execute(text("""
            SELECT r.name, COUNT(d.id), COUNT(d.geom)
            FROM regions r LEFT JOIN districts d ON d.region_id = r.id
            GROUP BY r.name ORDER BY r.name
        """)).fetchall()
    
    print(f"\nFinal stats:")
    total_d = total_g = 0
    for name, cnt, gcnt in stats:
        total_d += cnt
        total_g += gcnt
        if gcnt < cnt:
            print(f"  {cnt:4d} ({gcnt:4d} geom)  {name}")
    print(f"\nTotal: {total_d} districts, {total_g} with geometry")


if __name__ == "__main__":
    main()
