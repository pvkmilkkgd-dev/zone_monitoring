"""Apply official ОКТМО names from classinform.ru (актуальный с изм. до 01.02.2026).
Handles the fact that ОКТМО names may or may not include the type designation.
When type is missing, it's composed from the category (МО/МР/ГО/ЗАТО).
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

AUTONOMOUS_OKRUGS = {
    'Ненецкий автономный округ': {'parent_code': '11', 'section': '11100'},
    'Ханты-Мансийский автономный округ - Югра': {'parent_code': '71', 'section': '71800'},
    'Ямало-Ненецкий автономный округ': {'parent_code': '71', 'section': '71900'},
}

# Types based on category code digit (3rd digit of the category code)
TYPE_MAP = {
    '5': 'МО',   # Муниципальные округа
    '6': 'МР',   # Муниципальные районы
    '7': 'ГО',   # Городские округа
    '8': 'ВГТ',  # Внутригородские территории (for Moscow/SPb/Sevastopol)
}


def fetch_page(url):
    """Fetch and parse a page with retry."""
    for attempt in range(3):
        try:
            time.sleep(1.5)
            resp = requests.get(url, headers=HEADERS, timeout=60)
            if resp.status_code == 200:
                return BeautifulSoup(resp.text, 'html.parser')
            if resp.status_code == 404:
                return None
            print(f"  HTTP {resp.status_code} for {url}")
        except Exception as e:
            print(f"  Error fetching {url}: {e}")
            time.sleep(3)
    return None


def has_type_designation(name):
    """Check if name already includes a type designation."""
    lower = name.lower()
    type_words = [
        'муниципальный район', 'муниципальный округ', 'городской округ',
        'город ', 'зато ', 'зато', 'муниципальное образование',
    ]
    return any(w in lower for w in type_words)


def is_adjective_name(name):
    """Check if name looks like an adjective (ending in -ский, -ской, -ный, etc.)."""
    lower = name.strip().lower()
    adj_endings = ['ский', 'ской', 'ная', 'ное', 'ный', 'кий', 'ное', 'чий', 'жий',
                   'ший', 'ний', 'тий', 'зий', 'вий']
    return any(lower.endswith(e) for e in adj_endings)


def compose_full_name(name, category_type):
    """Compose full official name with type designation if missing."""
    if has_type_designation(name):
        return name
    
    name = name.strip()
    
    if category_type == 'МО':  # Муниципальный округ
        if is_adjective_name(name):
            return f"{name} муниципальный округ"
        else:
            return f"муниципальный округ {name}"
    
    elif category_type == 'МР':  # Муниципальный район
        if is_adjective_name(name):
            return f"{name} муниципальный район"
        else:
            return f"муниципальный район {name}"
    
    elif category_type == 'ГО':  # Городской округ
        # Check if it starts with "город " already
        if name.lower().startswith('город '):
            return name
        # Check for ЗАТО
        if name.upper().startswith('ЗАТО'):
            return name
        # Adjective names -> "X городской округ"
        if is_adjective_name(name):
            return f"{name} городской округ"
        # City/noun names -> "город X" or "городской округ X"
        return f"городской округ {name}"
    
    elif category_type == 'ВГТ':  # Internal city territories (Moscow etc.)
        return name  # Keep as-is
    
    return name


def extract_names_with_types(soup, prefix):
    """Extract names from a category page, preserving original names."""
    names = []
    body = soup.find('body')
    if not body:
        return names
    
    text = body.get_text('\n', strip=True)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        # Check if this line is an 8-digit ОКТМО code
        if re.match(r'^\d{8}$', line) and line.startswith(prefix[:2]):
            code = line
            # Skip category headers (ending with 00000)
            if code.endswith('00000') or code.endswith('0000'):
                i += 1
                continue
            # Next line is the name
            if i + 1 < len(lines):
                name_line = lines[i + 1]
                # Skip metadata/codes
                if not name_line[0].isdigit() and 'ОКТМО' not in name_line and 'включен' not in name_line.lower() and 'действует' not in name_line.lower():
                    # Clean: remove (admin center) part
                    name = re.sub(r'\s*\(.*?\)\s*$', '', name_line).strip()
                    if name and len(name) > 1:
                        names.append(name)
        i += 1
    
    return names


def normalize(name):
    """Normalize name for fuzzy matching."""
    n = name.strip().lower()
    for w in ['муниципальный район', 'муниципальный округ', 'городской округ',
              'район', 'округ', 'городской', 'город', 'зато', 'муниципальный',
              'муниципальное образование', 'муниципальное', 'национальный',
              'муниципальныйокруг']:  # Handle potential parsing glitch
        n = n.replace(w, '')
    n = re.sub(r'[«»"\'\-\s]', '', n)
    n = n.replace('ё', 'е')
    return n.strip()


def fetch_region_all_districts(code):
    """Fetch all official district names with types for a region."""
    all_entries = []  # list of (name, category_type)
    
    # Fetch main region page to discover categories
    main_url = f"{BASE}/oktmo/{code}000000000.html"
    soup = fetch_page(main_url)
    if not soup:
        return all_entries
    
    # Find category links
    categories = []
    body = soup.find('body')
    text = body.get_text('\n', strip=True) if body else ''
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    for i, line in enumerate(lines):
        if re.match(r'^\d{8}$', line) and line.startswith(code):
            cat_digit = line[2]  # 3rd digit determines type
            if cat_digit in TYPE_MAP:
                categories.append((line, TYPE_MAP[cat_digit]))
    
    if not categories:
        # For some regions without sub-categories, extract directly
        names = extract_names_with_types(soup, code)
        for n in names:
            all_entries.append((n, 'ГО'))  # Default assumption
        return all_entries
    
    for cat_code, cat_type in categories:
        cat_url = f"{BASE}/oktmo/{cat_code}000.html"
        cat_soup = fetch_page(cat_url)
        if cat_soup:
            names = extract_names_with_types(cat_soup, code)
            for n in names:
                all_entries.append((n, cat_type))
    
    return all_entries


def fetch_ao_all_districts(ao_info):
    """Fetch districts for an autonomous okrug."""
    section = ao_info['section']
    all_entries = []
    
    # First try the section main page
    url = f"{BASE}/oktmo/{section}000000.html"
    soup = fetch_page(url)
    if not soup:
        return all_entries
    
    body = soup.find('body')
    text = body.get_text('\n', strip=True) if body else ''
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    # Find subcategories
    sub_cats = []
    for line in lines:
        if re.match(r'^\d{8}$', line) and line.startswith(section[:3]):
            cat_digit = line[3]  # For AO sections, digit position may differ
            # AO subcategories: XX1X5 = МО, XX1X6 = МР, XX1X7 = ГО
            if line[4] in ('5', '6', '7', '8'):
                ct = TYPE_MAP.get(line[4], 'ГО')
                sub_cats.append((line, ct))
    
    if sub_cats:
        for cat_code, cat_type in sub_cats:
            cat_url = f"{BASE}/oktmo/{cat_code}000.html"
            cat_soup = fetch_page(cat_url)
            if cat_soup:
                names = extract_names_with_types(cat_soup, section[:2])
                for n in names:
                    all_entries.append((n, cat_type))
    else:
        # Try extracting from the main AO page
        names = extract_names_with_types(soup, section[:2])
        for n in names:
            all_entries.append((n, 'ГО'))
    
    return all_entries


# ============ MAIN ============
with ENGINE.connect() as c:
    db_regions = c.execute(text("SELECT id, name FROM regions ORDER BY name")).fetchall()

total_fixed = 0
total_matched = 0
total_unmatched_db = 0
regions_done = 0

for region_id, region_name in db_regions:
    region_id = str(region_id)
    
    # Find ОКТМО code
    oktmo_code = None
    ao_info = None
    
    if region_name in AUTONOMOUS_OKRUGS:
        ao_info = AUTONOMOUS_OKRUGS[region_name]
    else:
        for code, name in REGION_CODE_MAP.items():
            if name == region_name:
                oktmo_code = code
                break
    
    if not oktmo_code and not ao_info:
        print(f"\n{region_name}: NO ОКТМО CODE - SKIP")
        continue
    
    # Fetch official names
    if ao_info:
        print(f"\n{region_name} (AO {ao_info['section']}):")
        entries = fetch_ao_all_districts(ao_info)
    else:
        print(f"\n{region_name} (code {oktmo_code}):")
        entries = fetch_region_all_districts(oktmo_code)
    
    if not entries:
        print(f"  NO DATA")
        continue
    
    # Compose full names with types
    official_names = {}  # norm -> full_name
    for raw_name, cat_type in entries:
        full_name = compose_full_name(raw_name, cat_type)
        n = normalize(raw_name)
        official_names[n] = full_name
    
    print(f"  ОКТМО entries: {len(official_names)}")
    
    # Get DB districts
    with ENGINE.connect() as c:
        db_districts = c.execute(text(
            "SELECT id, name FROM districts WHERE region_id = :rid ORDER BY name"
        ), {'rid': region_id}).fetchall()
    
    print(f"  DB districts: {len(db_districts)}")
    
    # Match and update
    fixes = []
    matched = 0
    unmatched = []
    
    for did, dname in db_districts:
        d_norm = normalize(dname)
        if d_norm in official_names:
            full_name = official_names[d_norm]
            matched += 1
            if full_name != dname:
                fixes.append((str(did), dname, full_name))
        else:
            unmatched.append(dname)
    
    total_matched += matched
    
    if fixes:
        print(f"  Renaming {len(fixes)}:")
        with ENGINE.begin() as c:
            for did, old, new in fixes:
                print(f"    {old} -> {new}")
                c.execute(text("UPDATE districts SET name = :new WHERE id = :id"),
                         {'new': new, 'id': did})
        total_fixed += len(fixes)
    else:
        print(f"  No changes needed (matched {matched})")
    
    if unmatched:
        total_unmatched_db += len(unmatched)
        for n in unmatched[:5]:
            print(f"  UNMATCHED: {n}")
        if len(unmatched) > 5:
            print(f"  ... and {len(unmatched)-5} more unmatched")
    
    regions_done += 1

print(f"\n\n{'='*60}")
print(f"DONE! Regions: {regions_done}, Matched: {total_matched}, Fixed: {total_fixed}, Unmatched DB: {total_unmatched_db}")
