"""
Complete reload of ALL districts for ALL regions from OSM.
Then rename to ОКТМО official names.
Step 1: Overpass (relation IDs) + Nominatim (geometry by ID) for all 89 regions
Step 2: Rename to ОКТМО names
"""
import sys, os, re, json, time, requests
from uuid import uuid4
from bs4 import BeautifulSoup

os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

REGION_OSM_NAMES = {
    "город Москва": "Москва",
    "город Санкт-Петербург": "Санкт-Петербург",
    "город Севастополь": "Севастополь",
}

REGION_ADMIN_LEVELS = {
    "город Москва": "5",
    "город Санкт-Петербург": "5",
    "город Севастополь": "5",
}

NOMINATIM_REGIONS = {
    "Донецкая Народная Республика": [
        "Бердянский район", "Васильевский район", "Мелитопольский район",
        "Пологовский район", "Запорожский район",
    ],
}


def get_osm_relations(region_name):
    osm_name = REGION_OSM_NAMES.get(region_name, region_name)
    al = REGION_ADMIN_LEVELS.get(region_name, "6")
    
    for region_al in ["4", "3"]:
        query = f"""
[out:json][timeout:120];
area["name"="{osm_name}"]["admin_level"="{region_al}"]->.region;
relation["boundary"="administrative"]["admin_level"~"^({al})$"](area.region);
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
                if result:
                    return result
        except Exception as e:
            print(f"    Overpass err: {e}")
    
    # Fallback: try level 5|6|7
    for region_al in ["4", "3"]:
        query = f"""
[out:json][timeout:120];
area["name"="{osm_name}"]["admin_level"="{region_al}"]->.region;
relation["boundary"="administrative"]["admin_level"~"^(5|6|7)$"](area.region);
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
                if result:
                    return result
        except:
            pass
    
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


def load_region_osm(region_id, region_name):
    """Load all districts from OSM for a region."""
    relations = get_osm_relations(region_name)
    if not relations:
        return -1  # Failed
    
    # Clear
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
    
    return inserted


# ===== ОКТМО =====
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

OKTMO_EXCLUDES = {
    "Архангельская область": "118",
    "Тюменская область": ("711", "7114"),
}

NO_OKTMO = {
    "Донецкая Народная Республика", "Луганская Народная Республика",
    "Запорожская область", "Херсонская область",
    "Ненецкий автономный округ", "Ханты-Мансийский автономный округ - Югра",
    "Ямало-Ненецкий автономный округ",
}


def fetch_oktmo_names(code, exclude_prefix=None):
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
    if 'внутригородское' in name.lower() or 'внутригородской' in name.lower():
        return name
    if 'поселение' in name.lower():
        return name
    m = re.match(r'^город\s+(.+)$', name)
    if m:
        return f"городской округ {m.group(1)}"
    return name


def rename_oktmo(region_id, region_name):
    """Rename-only pass for ОКТМО names."""
    oktmo_code = REGION_TO_OKTMO.get(region_name)
    if not oktmo_code:
        return 0
    
    exclude = OKTMO_EXCLUDES.get(region_name)
    oktmo_raw = fetch_oktmo_names(oktmo_code, exclude)
    oktmo_names = [transform_name(n) for n in oktmo_raw]
    
    with ENGINE.connect() as conn:
        rows = conn.execute(text(
            "SELECT id, name FROM districts WHERE region_id = :rid"
        ), {"rid": region_id}).fetchall()
    
    db_by_norm = {}
    for did, dname in rows:
        db_by_norm[normalize(dname)] = (str(did), dname)
    
    renames = 0
    for target in oktmo_names:
        tnorm = normalize(target)
        if tnorm in db_by_norm:
            did, dname = db_by_norm[tnorm]
            if dname != target:
                with ENGINE.connect() as conn:
                    conn.execute(text("UPDATE districts SET name = :n WHERE id = :id"),
                               {"n": target, "id": did})
                    conn.commit()
                renames += 1
    return renames


def main():
    # Get all regions
    with ENGINE.connect() as conn:
        regions = conn.execute(text("SELECT id, name FROM regions ORDER BY name")).fetchall()
    regions = [(str(r[0]), r[1]) for r in regions]
    
    print(f"{'='*70}")
    print(f"STEP 1: Load ALL districts from OSM ({len(regions)} regions)")
    print(f"{'='*70}\n")
    
    failed = []
    total_loaded = 0
    
    for i, (rid, rname) in enumerate(regions):
        print(f"[{i+1}/{len(regions)}] {rname}")
        
        n = load_region_osm(rid, rname)
        if n < 0:
            print(f"    FAILED")
            failed.append(rname)
        elif n == 0:
            print(f"    EMPTY")
            failed.append(rname)
        else:
            print(f"    OK: {n}")
            total_loaded += n
        
        time.sleep(2)
    
    print(f"\n{'='*70}")
    print(f"Step 1 done: {total_loaded} districts loaded")
    if failed:
        print(f"Failed ({len(failed)}): {', '.join(failed)}")
    
    # Step 2: Rename
    print(f"\n{'='*70}")
    print(f"STEP 2: Rename to ОКТМО names")
    print(f"{'='*70}\n")
    
    total_renames = 0
    for rid, rname in regions:
        if rname in NO_OKTMO:
            continue
        r = rename_oktmo(rid, rname)
        if r:
            print(f"  {rname}: {r} renames")
            total_renames += r
        time.sleep(0.5)
    
    print(f"\nTotal renames: {total_renames}")
    
    # Final
    with ENGINE.connect() as conn:
        stats = conn.execute(text("""
            SELECT COUNT(d.id), COUNT(d.geom) FROM districts d
        """)).fetchone()
    print(f"\nFinal: {stats[0]} districts, {stats[1]} with geometry")


if __name__ == "__main__":
    main()
