"""Apply OFFICIAL ОКТМО names to ALL districts. 
Source: okp-okpd.ru/oktmo.aspx (Federal classifier ОКТМО ОК 033-2013)
ONLY renames — never adds or deletes districts."""
import sys, os, re, time, requests
from bs4 import BeautifulSoup

os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)

# ОКТМО code -> DB region name
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

# Autonomous okrugs: take subset of parent code
AUTONOMOUS_OKRUGS = {
    "Ненецкий автономный округ": {"parent_code": "11", "prefix": "118"},
    "Ханты-Мансийский автономный округ — Югра": {"parent_code": "71", "prefix": "711"},
    "Ханты-Мансийский автономный округ - Югра": {"parent_code": "71", "prefix": "711"},
    "Ямало-Ненецкий автономный округ": {"parent_code": "71", "prefix": "7114"},
}

# Regions to skip (no ОКТМО data available)
SKIP = {
    "Донецкая Народная Республика",
    "Луганская Народная Республика",
    "Запорожская область",
    "Херсонская область",
}


def fetch_oktmo(code):
    """Fetch district names from ОКТМО classifier."""
    url = f"https://okp-okpd.ru/oktmo.aspx?kod={code}"
    try:
        resp = requests.get(url, timeout=30)
        resp.encoding = 'windows-1251'
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        districts = []
        for tr in soup.find_all('tr'):
            cells = tr.find_all('td')
            if len(cells) >= 2:
                code_text = cells[0].get_text(strip=True)
                name_text = cells[1].get_text(strip=True)
                if re.match(r'^\d{11}$', code_text) and name_text:
                    districts.append({'oktmo': code_text, 'name': name_text})
        return districts
    except Exception as e:
        print(f"    Fetch error: {e}")
        return None


def normalize(name):
    """Normalize for matching: strip type words."""
    n = name.strip().lower()
    for w in ['муниципальный район', 'муниципальный округ', 'городской округ',
              'район', 'округ', 'городской', 'город', 'зато', 'муниципальный',
              'внутригородское муниципальное образование',
              'внутригородской муниципальный округ',
              'муниципальное образование', 'поселение',
              'национальный', 'эвенкийский', 'улус', 'кожуун']:
        n = n.replace(w, '')
    n = n.replace('ё', 'е').replace('-', '').replace(' ', '').replace('«', '').replace('»', '').replace('"', '')
    return n.strip()


def transform_oktmo_name(name):
    """Transform ОКТМО name: 'город X' -> 'городской округ X'"""
    if 'внутригородское' in name.lower() or 'внутригородской' in name.lower():
        return name
    if 'поселение' in name.lower():
        return name
    m = re.match(r'^город\s+(.+)$', name)
    if m:
        return f"городской округ {m.group(1)}"
    return name


def process_region(region_name, oktmo_entries):
    """Match ОКТМО names to DB districts and rename."""
    with ENGINE.connect() as c:
        row = c.execute(text("SELECT id FROM regions WHERE name = :name"),
                       {'name': region_name}).fetchone()
    if not row:
        return 0
    region_id = str(row[0])
    
    # Get DB districts
    with ENGINE.connect() as c:
        db_rows = c.execute(text("""
            SELECT id, name FROM districts WHERE region_id = :rid
        """), {'rid': region_id}).fetchall()
    
    # Build ОКТМО lookup: normalized -> official name
    oktmo_by_norm = {}
    for entry in oktmo_entries:
        official = transform_oktmo_name(entry['name'])
        norm = normalize(official)
        oktmo_by_norm[norm] = official
    
    # Match and rename
    renamed = 0
    for did, dname in db_rows:
        d_norm = normalize(dname)
        if d_norm in oktmo_by_norm:
            official = oktmo_by_norm[d_norm]
            if official != dname:
                with ENGINE.begin() as c:
                    c.execute(text("UPDATE districts SET name = :new WHERE id = :id"),
                             {'new': official, 'id': str(did)})
                print(f"    {dname} -> {official}")
                renamed += 1
        else:
            # Try partial match
            for norm_key, official in oktmo_by_norm.items():
                if d_norm and len(d_norm) > 3 and (d_norm in norm_key or norm_key in d_norm):
                    if official != dname:
                        with ENGINE.begin() as c:
                            c.execute(text("UPDATE districts SET name = :new WHERE id = :id"),
                                     {'new': official, 'id': str(did)})
                        print(f"    {dname} -> {official} (partial)")
                        renamed += 1
                        break
    
    return renamed


# Build reverse mapping: region name -> ОКТМО code
region_to_code = {}
for code, name in OKTMO_TO_REGION.items():
    if name not in region_to_code or len(code) < len(region_to_code[name]):
        region_to_code[name] = code

# Get all regions from DB
with ENGINE.connect() as c:
    all_regions = c.execute(text("SELECT name FROM regions ORDER BY name")).fetchall()

total_renamed = 0
total_regions = 0

for (region_name,) in all_regions:
    if region_name in SKIP:
        continue
    
    # Check if autonomous okrug
    ao_config = AUTONOMOUS_OKRUGS.get(region_name)
    
    if ao_config:
        code = ao_config['parent_code']
        prefix = ao_config['prefix']
        print(f"\n{region_name} (ОКТМО {code}, prefix {prefix})")
        
        entries = fetch_oktmo(code)
        time.sleep(0.3)
        if not entries:
            print(f"  Failed to fetch ОКТМО")
            continue
        
        # Filter to only entries with matching prefix
        entries = [e for e in entries if e['oktmo'].startswith(prefix)]
        print(f"  {len(entries)} ОКТМО entries")
        
    elif region_name in region_to_code:
        code = region_to_code[region_name]
        print(f"\n{region_name} (ОКТМО {code})")
        
        entries = fetch_oktmo(code)
        time.sleep(0.3)
        if not entries:
            print(f"  Failed to fetch ОКТМО")
            continue
        
        # For parent regions with AO, exclude AO entries
        # Архангельская без НАО
        if region_name == 'Архангельская область':
            entries = [e for e in entries if not e['oktmo'].startswith('118')]
        elif region_name == 'Тюменская область':
            entries = [e for e in entries if not e['oktmo'].startswith('711') and not e['oktmo'].startswith('7114')]
        
        print(f"  {len(entries)} ОКТМО entries")
    else:
        continue
    
    renamed = process_region(region_name, entries)
    if renamed:
        total_renamed += renamed
    total_regions += 1

print(f"\n\n{'='*60}")
print(f"Done! Processed {total_regions} regions, renamed {total_renamed} districts")
print(f"{'='*60}")
