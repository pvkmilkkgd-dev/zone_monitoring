"""Rename districts with short names using ОКТМО official names.
SAFE: Only renames, never deletes or adds districts."""
import sys, os, re, time, requests
from bs4 import BeautifulSoup
from collections import defaultdict

os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)

# ОКТМО region codes
OKTMO_TO_REGION = {
    "01": "Алтайский край", "03": "Краснодарский край", "04": "Красноярский край",
    "05": "Приморский край", "07": "Ставропольский край", "08": "Хабаровский край",
    "10": "Амурская область", "11": "Архангельская область", "12": "Астраханская область",
    "14": "Белгородская область", "15": "Брянская область", "17": "Владимирская область",
    "18": "Волгоградская область", "19": "Вологодская область", "20": "Воронежская область",
    "22": "Нижегородская область", "24": "Ивановская область", "25": "Иркутская область",
    "26": "Республика Ингушетия", "27": "Калининградская область",
    "30": "Калужская область", "33": "Камчатский край",
    "35": "Кемеровская область", "36": "Кировская область",
    "37": "Костромская область", "38": "Курганская область",
    "39": "Курская область", "41": "Ленинградская область",
    "42": "Липецкая область", "44": "Магаданская область",
    "46": "Московская область", "49": "Мурманская область",
    "22": "Нижегородская область", "50": "Новгородская область",
    "52": "Новосибирская область", "53": "Омская область",
    "54": "Оренбургская область", "55": "Орловская область",
    "56": "Пензенская область", "57": "Пермский край",
    "58": "Псковская область", "60": "Ростовская область",
    "61": "Рязанская область", "63": "Самарская область",
    "64": "Саратовская область", "65": "Сахалинская область",
    "66": "Свердловская область", "67": "Смоленская область",
    "68": "Тамбовская область", "69": "Тверская область",
    "70": "Томская область", "71": "Тульская область",
    "72": "Тюменская область", "73": "Ульяновская область",
    "75": "Челябинская область", "76": "Забайкальский край",
    "78": "Ярославская область",
    "79": "Республика Адыгея", "80": "Республика Башкортостан",
    "81": "Республика Бурятия", "82": "Республика Дагестан",
    "83": "Республика Кабардино-Балкарская", "84": "Республика Алтай",
    "85": "Республика Калмыкия", "86": "Карачаево-Черкесская Республика",
    "87": "Республика Карелия", "88": "Республика Коми",
    "89": "Республика Марий Эл", "90": "Республика Мордовия",
    "92": "Республика Саха (Якутия)", "93": "Республика Северная Осетия — Алания",
    "94": "Республика Татарстан", "95": "Республика Тыва",
    "96": "Удмуртская Республика", "97": "Республика Хакасия",
    "98": "Чеченская Республика",  "99": "Чувашская Республика",
    "111": "Ненецкий автономный округ",
    "118": "Ненецкий автономный округ",
    "711": "Ханты-Мансийский автономный округ — Югра",
    "714": "Ямало-Ненецкий автономный округ",
    "77": "Еврейская автономная область",
    "91": "Чукотский автономный округ",
}

# Reverse: region name -> OKTMO code
REGION_TO_OKTMO = {}
for code, name in OKTMO_TO_REGION.items():
    if name not in REGION_TO_OKTMO or len(code) < len(REGION_TO_OKTMO[name]):
        REGION_TO_OKTMO[name] = code

# Aliases for region name matching
REGION_ALIASES = {
    "Кабардино-Балкарская Республика": "83",
}


def fetch_oktmo_names(code):
    """Fetch district names from ОКТМО for a region code."""
    url = f"https://okp-okpd.ru/oktmo.aspx?kod={code}"
    try:
        resp = requests.get(url, timeout=30)
        resp.encoding = 'windows-1251'
        if resp.status_code != 200:
            return []
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        names = []
        for tr in soup.find_all('tr'):
            cells = tr.find_all('td')
            if len(cells) >= 2:
                code_text = cells[0].get_text(strip=True)
                name_text = cells[1].get_text(strip=True)
                if re.match(r'^\d{11}$', code_text) and name_text:
                    names.append(name_text)
        return names
    except Exception as e:
        print(f"    Fetch error: {e}")
        return []


def normalize(name):
    """Normalize for matching: strip type words, lowercase, remove spaces/hyphens."""
    n = name.strip().lower()
    for w in ['муниципальный район', 'муниципальный округ', 'городской округ',
              'район', 'округ', 'городской', 'город', 'зато', 'муниципальный',
              'муниципальное образование', 'внутригородское муниципальное образование',
              'внутригородской муниципальный округ', 'поселение',
              'национальный', 'эвенкийский']:
        n = n.replace(w, '')
    n = n.replace('ё', 'е').replace('-', '').replace(' ', '').replace('«', '').replace('»', '').replace('"', '').replace("'", '')
    return n


def transform_name(name):
    """'город X' -> 'городской округ X'"""
    if 'внутригородское' in name.lower() or 'внутригородской' in name.lower():
        return name
    if 'поселение' in name.lower():
        return name
    m = re.match(r'^город\s+(.+)$', name)
    if m:
        return f"городской округ {m.group(1)}"
    return name


# Get all districts with short names
with ENGINE.connect() as c:
    rows = c.execute(text("""
        SELECT d.id, d.name, r.name as region_name
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE d.name NOT LIKE '%%район%%'
          AND d.name NOT LIKE '%%округ%%'
          AND d.name NOT LIKE '%%город%%'
          AND d.name NOT LIKE '%%ЗАТО%%'
          AND d.name NOT LIKE '%%поселение%%'
        ORDER BY r.name, d.name
    """)).fetchall()

by_region = defaultdict(list)
for r in rows:
    by_region[r[2]].append({'id': str(r[0]), 'name': r[1]})

print(f"Found {len(rows)} districts with short names across {len(by_region)} regions\n")

total_fixed = 0
total_failed = 0

for region_name, districts in sorted(by_region.items()):
    # Find OKTMO code for this region
    code = REGION_TO_OKTMO.get(region_name) or REGION_ALIASES.get(region_name)
    if not code:
        print(f"=== {region_name} -> NO OKTMO CODE, skipping ===")
        total_failed += len(districts)
        continue
    
    print(f"=== {region_name} (code={code}, {len(districts)} to fix) ===")
    
    oktmo_names = fetch_oktmo_names(code)
    time.sleep(0.3)
    
    if not oktmo_names:
        print(f"  Could not fetch OKTMO names")
        total_failed += len(districts)
        continue
    
    # Build normalized OKTМО lookup
    oktmo_by_norm = {}
    for oname in oktmo_names:
        transformed = transform_name(oname)
        norm = normalize(transformed)
        oktmo_by_norm[norm] = transformed
    
    for d in districts:
        d_norm = normalize(d['name'])
        
        if d_norm in oktmo_by_norm:
            new_name = oktmo_by_norm[d_norm]
            if new_name != d['name']:
                print(f"  {d['name']} -> {new_name}")
                with ENGINE.begin() as conn:
                    conn.execute(text("UPDATE districts SET name = :new WHERE id = :id"),
                               {'new': new_name, 'id': d['id']})
                total_fixed += 1
            else:
                print(f"  {d['name']} - already correct")
        else:
            # Try partial match
            found = False
            for norm_key, full_name in oktmo_by_norm.items():
                if d_norm in norm_key or norm_key in d_norm:
                    if full_name != d['name']:
                        print(f"  {d['name']} -> {full_name} (partial)")
                        with ENGINE.begin() as conn:
                            conn.execute(text("UPDATE districts SET name = :new WHERE id = :id"),
                                       {'new': full_name, 'id': d['id']})
                        total_fixed += 1
                        found = True
                        break
            if not found:
                print(f"  {d['name']} -> NO MATCH (norm={d_norm})")
                total_failed += 1

print(f"\n\nDone! Fixed: {total_fixed}, Failed: {total_failed}")
