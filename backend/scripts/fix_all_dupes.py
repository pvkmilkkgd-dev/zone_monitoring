"""Fix all duplicate district names within the same region.
For each duplicate pair, the smaller area is typically the city (ГО),
and the larger one is the surrounding district (МР/МО).
We check ОКТМО to determine the correct names.
"""
import sys, os, re, time, requests
from bs4 import BeautifulSoup

os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
BASE = "https://classinform.ru"
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html', 'Accept-Language': 'ru-RU,ru;q=0.9'}

CATEGORY_TYPES = {'5': 'МО', '6': 'МР', '7': 'ГО'}


def fetch_page(url):
    for attempt in range(3):
        try:
            time.sleep(1.2)
            resp = requests.get(url, headers=HEADERS, timeout=60)
            if resp.status_code == 200:
                return resp.text
        except:
            time.sleep(3)
    return None


def get_text_lines(html):
    soup = BeautifulSoup(html, 'html.parser')
    body = soup.find('body')
    return [l.strip() for l in body.get_text('\n', strip=True).split('\n') if l.strip()] if body else []


def normalize(name):
    n = name.strip().lower().replace('ё', 'е')
    for w in ['муниципальный район', 'муниципальный округ', 'городской округ',
              'муниципальный', 'район', 'округ', 'городской', 'город',
              'зато', 'национальный', 'долгано-эвенкийский']:
        n = n.replace(w, '')
    n = re.sub(r'[«»"\'\-\(\)\s]', '', n)
    return n.strip()


# Get all duplicates with area info
with ENGINE.connect() as c:
    dupes = c.execute(text("""
        SELECT d.id, d.name, r.name as rname, r.id as rid,
               ROUND(ST_Area(d.geom::geography)/1e6) as area_km2
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE (d.name, r.id) IN (
            SELECT d2.name, d2.region_id
            FROM districts d2
            GROUP BY d2.name, d2.region_id
            HAVING COUNT(*) > 1
        )
        ORDER BY r.name, d.name, ST_Area(d.geom::geography)
    """)).fetchall()

print(f"Found {len(dupes)} duplicate entries\n")

# Group by (name, region)
from collections import defaultdict
groups = defaultdict(list)
for did, dname, rname, rid, area in dupes:
    groups[(dname, rname, str(rid))].append((str(did), area))

# Region name -> ОКТМО code mapping
REGION_CODE_MAP = {
    'Карачаево-Черкесская Республика': '91',
    'Кемеровская область': '32',
    'Кировская область': '33',
    'Красноярский край': '04',
    'Пермский край': '57',
    'Приморский край': '05',
    'Республика Крым': '35',
    'Республика Саха (Якутия)': '98',
    'Республика Татарстан': '92',
    'Свердловская область': '65',
    'Челябинская область': '75',
}

# For each group, we need to figure out correct names from ОКТМО
for (dname, rname, rid), entries in sorted(groups.items()):
    entries.sort(key=lambda x: x[1])  # sort by area ascending
    print(f"\n=== [{rname}] {dname} ({len(entries)} dupes) ===")
    for did, area in entries:
        print(f"  id={did} area={area} km2")
    
    # For triples (like Эвенкийский x3), skip for now
    if len(entries) > 2:
        print(f"  SKIP: {len(entries)} entries, manual check needed")
        continue
    
    small_id, small_area = entries[0]
    large_id, large_area = entries[1]
    
    # If both are very similar in size, need manual check
    if small_area > 0 and large_area / max(small_area, 1) < 3:
        print(f"  SKIP: areas too similar ({small_area} vs {large_area}), manual check needed")
        continue
    
    # Fetch ОКТМО to find correct names
    oktmo_code = REGION_CODE_MAP.get(rname)
    if not oktmo_code:
        print(f"  SKIP: no ОКТМО code for {rname}")
        continue
    
    # Search through all categories
    name_norm = normalize(dname)
    found_names = {}  # cat_type -> name
    
    main_html = fetch_page(f"{BASE}/oktmo/{oktmo_code}000000000.html")
    if not main_html:
        print(f"  SKIP: could not fetch main page")
        continue
    
    lines = get_text_lines(main_html)
    cats = []
    for line in lines:
        if re.match(r'^\d{8}$', line) and line.startswith(oktmo_code):
            if line[3:] == '00000' and line[2] in CATEGORY_TYPES:
                cats.append((line, CATEGORY_TYPES[line[2]]))
    
    for cat_code, cat_type in cats:
        cat_html = fetch_page(f"{BASE}/oktmo/{cat_code}000.html")
        if not cat_html:
            continue
        cat_lines = get_text_lines(cat_html)
        i = 0
        while i < len(cat_lines):
            if re.match(r'^\d{8}$', cat_lines[i]) and cat_lines[i][3:] != '00000':
                if i + 1 < len(cat_lines):
                    entry_name = re.sub(r'\s*\([^)]*\)\s*$', '', cat_lines[i+1]).strip()
                    if normalize(entry_name) == name_norm:
                        found_names[cat_type] = entry_name
            i += 1
    
    if found_names:
        print(f"  ОКТМО matches: {found_names}")
        
        # Determine correct assignment
        # Small area = city (ГО), large area = district (МО/МР)
        go_name = found_names.get('ГО')
        mo_name = found_names.get('МО')
        mr_name = found_names.get('МР')
        
        district_name = mo_name or mr_name
        city_name = go_name
        
        if city_name and district_name:
            print(f"  FIX: small ({small_area}km2) -> '{city_name}' (ГО)")
            print(f"  FIX: large ({large_area}km2) -> '{district_name}' (МО/МР)")
            
            with ENGINE.begin() as c:
                # Update small (city)
                if city_name != dname:
                    c.execute(text("UPDATE districts SET name = :n WHERE id = :id"),
                             {'n': city_name, 'id': small_id})
                # Update large (district)
                if district_name != dname:
                    c.execute(text("UPDATE districts SET name = :n WHERE id = :id"),
                             {'n': district_name, 'id': large_id})
        elif district_name and not city_name:
            # Only district found in ОКТМО - the small one might be wrong
            print(f"  Only МО/МР found: '{district_name}'")
            print(f"  Large ({large_area}km2) -> '{district_name}'")
            if district_name != dname:
                with ENGINE.begin() as c:
                    c.execute(text("UPDATE districts SET name = :n WHERE id = :id"),
                             {'n': district_name, 'id': large_id})
        else:
            print(f"  Could not determine fix from ОКТМО names")
    else:
        print(f"  No ОКТМО matches found")

# Final dupe check
print("\n\n=== Remaining duplicates ===")
with ENGINE.connect() as c:
    rows = c.execute(text("""
        SELECT d.name, r.name, COUNT(*)
        FROM districts d JOIN regions r ON d.region_id = r.id
        GROUP BY d.name, r.name HAVING COUNT(*) > 1
        ORDER BY r.name
    """)).fetchall()
    if rows:
        for dname, rname, cnt in rows:
            print(f"  [{rname}] {dname} x{cnt}")
    else:
        print("  Нет!")

print("\nDone!")
