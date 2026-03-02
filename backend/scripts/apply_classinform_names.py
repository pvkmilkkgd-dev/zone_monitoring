"""Apply official ОКТМО names from classinform.ru (актуальный с изм. до 01.02.2026)
to all districts in the database.

classinform.ru structure:
  /oktmo/XXYYYZZZZZZ.html
  XX = region code (01..99)
  Main page: /oktmo/XX000000000.html -> lists categories:
    XX500000000 = Муниципальные округа
    XX600000000 = Муниципальные районы
    XX700000000 = Городские округа
  Each category page lists districts with their official names.
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
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'ru-RU,ru;q=0.9',
}

# Mapping of ОКТМО region codes to DB region names
# Built from classinform.ru main page + DB region list
REGION_CODE_MAP = {
    '01': 'Алтайский край',
    '03': 'Краснодарский край',
    '04': 'Красноярский край',
    '05': 'Приморский край',
    '07': 'Ставропольский край',
    '08': 'Хабаровский край',
    '10': 'Амурская область',
    '11': 'Архангельская область',
    '12': 'Астраханская область',
    '14': 'Белгородская область',
    '15': 'Брянская область',
    '17': 'Владимирская область',
    '18': 'Волгоградская область',
    '19': 'Вологодская область',
    '20': 'Воронежская область',
    '21': 'Донецкая Народная Республика',
    '22': 'Нижегородская область',
    '23': 'Запорожская область',
    '24': 'Ивановская область',
    '25': 'Иркутская область',
    '26': 'Республика Ингушетия',
    '27': 'Калининградская область',
    '28': 'Тверская область',
    '29': 'Калужская область',
    '30': 'Камчатский край',
    '32': 'Кемеровская область',
    '33': 'Кировская область',
    '34': 'Костромская область',
    '35': 'Республика Крым',
    '36': 'Самарская область',
    '37': 'Курганская область',
    '38': 'Курская область',
    '40': 'город Санкт-Петербург',
    '41': 'Ленинградская область',
    '42': 'Липецкая область',
    '43': 'Луганская Народная Республика',
    '44': 'Магаданская область',
    '45': 'город Москва',
    '46': 'Московская область',
    '47': 'Мурманская область',
    '49': 'Новгородская область',
    '50': 'Новосибирская область',
    '52': 'Омская область',
    '53': 'Оренбургская область',
    '54': 'Орловская область',
    '56': 'Пензенская область',
    '57': 'Пермский край',
    '58': 'Псковская область',
    '60': 'Ростовская область',
    '61': 'Рязанская область',
    '63': 'Саратовская область',
    '64': 'Сахалинская область',
    '65': 'Свердловская область',
    '66': 'Смоленская область',
    '67': 'город Севастополь',
    '68': 'Тамбовская область',
    '69': 'Томская область',
    '70': 'Тульская область',
    '71': 'Тюменская область',
    '73': 'Ульяновская область',
    '74': 'Херсонская область',
    '75': 'Челябинская область',
    '76': 'Забайкальский край',
    '77': 'Чукотский автономный округ',
    '78': 'Ярославская область',
    '79': 'Республика Адыгея',
    '80': 'Республика Башкортостан',
    '81': 'Республика Бурятия',
    '82': 'Республика Дагестан',
    '83': 'Кабардино-Балкарская Республика',
    '84': 'Республика Алтай',
    '85': 'Республика Калмыкия',
    '86': 'Республика Карелия',
    '87': 'Республика Коми',
    '88': 'Республика Марий Эл',
    '89': 'Республика Мордовия',
    '90': 'Республика Северная Осетия - Алания',
    '91': 'Карачаево-Черкесская Республика',
    '92': 'Республика Татарстан',
    '93': 'Республика Тыва',
    '94': 'Удмуртская Республика',
    '95': 'Республика Хакасия',
    '96': 'Чеченская Республика',
    '97': 'Чувашская Республика',
    '98': 'Республика Саха (Якутия)',
    '99': 'Еврейская автономная область',
}

# Autonomous okrugs that are separate regions but part of parent region in ОКТМО
# These need special handling - they have their own sub-sections within the parent code
AUTONOMOUS_OKRUGS = {
    'Ненецкий автономный округ': {'parent_code': '11', 'section': '11100'},  # inside Arkhangelsk
    'Ханты-Мансийский автономный округ - Югра': {'parent_code': '71', 'section': '71800'},  # inside Tyumen
    'Ямало-Ненецкий автономный округ': {'parent_code': '71', 'section': '71900'},  # inside Tyumen
}


def fetch_page(url):
    """Fetch and parse a page with retry."""
    for attempt in range(3):
        try:
            time.sleep(1.5)
            resp = requests.get(url, headers=HEADERS, timeout=60)
            if resp.status_code == 200:
                return BeautifulSoup(resp.text, 'html.parser')
            print(f"  HTTP {resp.status_code} for {url}")
        except Exception as e:
            print(f"  Error fetching {url}: {e}")
            time.sleep(3)
    return None


def extract_district_names(soup, prefix):
    """Extract district names from a category page on classinform.ru.
    Returns list of official names (without admin center in parentheses).
    """
    names = []
    body = soup.find('body')
    if not body:
        return names
    
    text = body.get_text('\n', strip=True)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    # Find pattern: code on one line, name on next, admin center in () on next
    i = 0
    while i < len(lines):
        line = lines[i]
        # Check if this line is an ОКТМО code (8-digit)
        if re.match(r'^\d{8}$', line) and line.startswith(prefix[:2]):
            code = line
            # Next line should be the name
            if i + 1 < len(lines):
                name_line = lines[i + 1]
                # Skip if it's another code or metadata
                if not name_line[0].isdigit() and 'ОКТМО' not in name_line and 'включен' not in name_line.lower():
                    # Clean: remove (admin center) part if accidentally joined
                    name = re.sub(r'\s*\(.*?\)\s*$', '', name_line).strip()
                    if name and len(name) > 2:
                        names.append(name)
        i += 1
    
    return names


def normalize(name):
    """Normalize name for fuzzy matching."""
    n = name.strip().lower()
    # Remove common prefixes/suffixes for matching
    for w in ['муниципальный район', 'муниципальный округ', 'городской округ',
              'район', 'округ', 'городской', 'город', 'зато', 'муниципальный',
              'муниципальное образование', 'муниципальное', 'национальный']:
        n = n.replace(w, '')
    n = re.sub(r'[«»"\'\-\s]', '', n)
    n = n.replace('ё', 'е')
    return n.strip()


def fetch_region_districts(code):
    """Fetch all official district names for a region from classinform.ru."""
    all_names = []
    
    # First fetch main region page to discover categories
    main_url = f"{BASE}/oktmo/{code}000000000.html"
    soup = fetch_page(main_url)
    if not soup:
        return all_names
    
    # Find category links (XX5, XX6, XX7 for МО, МР, ГО)
    categories = []
    for a in soup.find_all('a'):
        href = a.get('href', '')
        atext = a.get_text(strip=True)
        m = re.search(r'/oktmo/(\d{11})\.html', href)
        if m:
            cat_code = m.group(1)
            # Categories end with 00000000 (like 01500000000, 01600000000, 01700000000)
            if cat_code[2:].startswith(('5', '6', '7', '8', '9')) and cat_code.endswith('00000000'):
                categories.append((cat_code, atext))
            # Also check for sub-sections like autonomous okrug sections
            elif cat_code[2:5] in ('100', '800', '900') and cat_code.endswith('00000000'):
                categories.append((cat_code, atext))
    
    if not categories:
        # Try to extract names directly from main page
        return extract_district_names(soup, code)
    
    for cat_code, cat_name in categories:
        cat_url = f"{BASE}/oktmo/{cat_code}.html"
        cat_soup = fetch_page(cat_url)
        if cat_soup:
            names = extract_district_names(cat_soup, code)
            all_names.extend(names)
    
    return all_names


def fetch_ao_districts(ao_info):
    """Fetch districts for an autonomous okrug (subsection of parent region)."""
    section = ao_info['section']
    all_names = []
    
    # Fetch the section page (e.g., 11100000000 for Nenets AO within Arkhangelsk)
    url = f"{BASE}/oktmo/{section}000000.html"
    soup = fetch_page(url)
    if not soup:
        return all_names
    
    # Find subcategories within the AO section
    categories = []
    for a in soup.find_all('a'):
        href = a.get('href', '')
        m = re.search(r'/oktmo/(\d{11})\.html', href)
        if m:
            cat_code = m.group(1)
            if cat_code.startswith(section[:3]) and cat_code != f"{section}000000" and cat_code.endswith('00000000'):
                categories.append(cat_code)
    
    if categories:
        for cat_code in categories:
            cat_url = f"{BASE}/oktmo/{cat_code}.html"
            cat_soup = fetch_page(cat_url)
            if cat_soup:
                names = extract_district_names(cat_soup, section[:2])
                all_names.extend(names)
    else:
        # Try to extract directly
        all_names = extract_district_names(soup, section[:2])
    
    return all_names


# ============ MAIN ============

# Get all regions from DB
with ENGINE.connect() as c:
    db_regions = c.execute(text("SELECT id, name FROM regions ORDER BY name")).fetchall()

total_fixed = 0
total_matched = 0
total_unmatched = 0

for region_id, region_name in db_regions:
    region_id = str(region_id)
    
    # Find ОКТМО code for this region
    oktmo_code = None
    ao_info = None
    
    # Check if it's an autonomous okrug
    if region_name in AUTONOMOUS_OKRUGS:
        ao_info = AUTONOMOUS_OKRUGS[region_name]
    else:
        for code, name in REGION_CODE_MAP.items():
            if name == region_name:
                oktmo_code = code
                break
    
    if not oktmo_code and not ao_info:
        print(f"\n{region_name}: NO ОКТМО CODE MAPPED - SKIPPING")
        continue
    
    # Fetch official names from classinform.ru
    if ao_info:
        print(f"\n{region_name} (AO section {ao_info['section']}):")
        oktmo_names = fetch_ao_districts(ao_info)
    else:
        print(f"\n{region_name} (code {oktmo_code}):")
        oktmo_names = fetch_region_districts(oktmo_code)
    
    if not oktmo_names:
        print(f"  NO NAMES FETCHED")
        continue
    
    print(f"  ОКТМО names: {len(oktmo_names)}")
    
    # Get DB districts
    with ENGINE.connect() as c:
        db_districts = c.execute(text(
            "SELECT id, name FROM districts WHERE region_id = :rid ORDER BY name"
        ), {'rid': region_id}).fetchall()
    
    print(f"  DB districts: {len(db_districts)}")
    
    # Build normalized lookup: norm -> official name
    oktmo_lookup = {}
    for name in oktmo_names:
        n = normalize(name)
        oktmo_lookup[n] = name
    
    # Match and update
    fixes = []
    matched = 0
    unmatched_db = []
    
    for did, dname in db_districts:
        d_norm = normalize(dname)
        if d_norm in oktmo_lookup:
            official_name = oktmo_lookup[d_norm]
            matched += 1
            if official_name != dname:
                fixes.append((str(did), dname, official_name))
        else:
            unmatched_db.append(dname)
    
    total_matched += matched
    
    if fixes:
        print(f"  Renaming {len(fixes)}:")
        with ENGINE.begin() as c:
            for did, old, new in fixes:
                print(f"    {old} -> {new}")
                c.execute(text("UPDATE districts SET name = :new WHERE id = :id"),
                         {'new': new, 'id': did})
        total_fixed += len(fixes)
    
    if unmatched_db:
        total_unmatched += len(unmatched_db)
        if len(unmatched_db) <= 5:
            for n in unmatched_db:
                print(f"  UNMATCHED DB: {n}")
        else:
            print(f"  UNMATCHED DB: {len(unmatched_db)} districts")
            for n in unmatched_db[:3]:
                print(f"    {n}")
            print(f"    ... and {len(unmatched_db)-3} more")

print(f"\n\n{'='*60}")
print(f"DONE! Matched: {total_matched}, Fixed: {total_fixed}, Unmatched: {total_unmatched}")
