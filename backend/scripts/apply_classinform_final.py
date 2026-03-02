"""Apply official ОКТМО names from classinform.ru (актуальный с изм. до 01.02.2026).

Strategy:
1. For each region, fetch main page -> discover category pages (МО, МР, ГО)
2. For each category page, extract (code, raw_name) pairs
3. If raw_name doesn't include type, compose full name using category type
4. Match to DB districts by normalized name
5. Update DB

This script handles autonomous okrugs separately.
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

# Mapping of ОКТМО region codes -> DB region names
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

# Autonomous okrugs within parent regions
AUTONOMOUS_OKRUGS = {
    'Ненецкий автономный округ': '11',   # inside Arkhangelsk
    'Ханты-Мансийский автономный округ - Югра': '71',  # inside Tyumen
    'Ямало-Ненецкий автономный округ': '71',  # inside Tyumen
}

# Category type by section digit
CATEGORY_TYPES = {
    '5': 'МО',   # Муниципальные округа
    '6': 'МР',   # Муниципальные районы
    '7': 'ГО',   # Городские округа
    '8': 'ВГТ',  # Внутригородские территории
}


def fetch_page(url):
    for attempt in range(3):
        try:
            time.sleep(1.2)
            resp = requests.get(url, headers=HEADERS, timeout=60)
            if resp.status_code == 200:
                return resp.text
            if resp.status_code == 404:
                return None
        except Exception as e:
            print(f"  ERR {url}: {e}")
            time.sleep(3)
    return None


def get_text_lines(html):
    """Get cleaned text lines from HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    body = soup.find('body')
    if not body:
        return []
    text = body.get_text('\n', strip=True)
    return [l.strip() for l in text.split('\n') if l.strip()]


def extract_entries_from_category_page(html):
    """Extract (code, name) pairs from a category page.
    Returns list of (8-digit_code, name_string).
    """
    lines = get_text_lines(html)
    entries = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Is this an 8-digit ОКТМО code?
        if re.match(r'^\d{8}$', line):
            code = line
            # Skip if this is a category/section header (last 5+ digits are zeros)
            if code[3:] == '00000':
                i += 1
                continue
            # Also skip region-level headers (XX000000)
            if code[2:] == '000000':
                i += 1
                continue
            # Next non-metadata line is the name
            j = i + 1
            while j < len(lines):
                candidate = lines[j]
                # Skip annotations like "(включен изменением...)" or "(действует с...)"
                if candidate.startswith('(') and ('включен' in candidate.lower() or 'действует' in candidate.lower() or 'исключен' in candidate.lower()):
                    j += 1
                    continue
                # Skip if it's another code
                if re.match(r'^\d{8}$', candidate):
                    break
                # Skip metadata
                if 'Полная расшифровка' in candidate or 'ОКТМО' in candidate:
                    break
                # This should be the name
                # Remove (admin center) suffix
                name = re.sub(r'\s*\([^)]*\)\s*$', '', candidate).strip()
                if name and len(name) > 1 and not name[0].isdigit():
                    entries.append((code, name))
                break
            i = j if j > i + 1 else i + 1
        else:
            i += 1
    return entries


def has_type(name):
    """Check if name already includes a type designation."""
    lower = name.lower()
    keywords = [
        'муниципальный район', 'муниципальный округ', 'городской округ',
        'город ', 'зато ', 'муниципальное образование',
        'рабочий поселок', 'поселок городского типа',
    ]
    return any(k in lower for k in keywords)


def is_adjective(name):
    """Check if name looks like an adjective form."""
    word = name.split()[-1].lower() if name.split() else ''
    return any(word.endswith(e) for e in [
        'ский', 'ской', 'ная', 'ное', 'ный', 'кий', 'жий',
        'ший', 'ний', 'тий', 'зий', 'вий', 'чий',
    ])


def compose_name(raw_name, cat_type):
    """Compose full name with type if missing."""
    # Already has type? Use as-is
    if has_type(raw_name):
        return raw_name
    
    # ЗАТО
    if raw_name.upper().startswith('ЗАТО'):
        return raw_name
    
    name = raw_name.strip()
    
    if cat_type == 'МО':
        return f"{name} муниципальный округ" if is_adjective(name) else f"муниципальный округ {name}"
    elif cat_type == 'МР':
        return f"{name} муниципальный район" if is_adjective(name) else f"муниципальный район {name}"
    elif cat_type == 'ГО':
        if is_adjective(name):
            return f"{name} городской округ"
        else:
            return f"городской округ {name}"
    elif cat_type == 'ВГТ':
        return name  # Internal city districts, keep as-is
    
    return name


def normalize(name):
    """Normalize for matching: strip type words, lowercase, remove punctuation."""
    n = name.strip().lower()
    # Normalize ё -> е
    n = n.replace('ё', 'е')
    # Remove all type designations
    for w in ['муниципальный район', 'муниципальный округ', 'муниципальныйокруг',
              'городской округ', 'муниципальное образование',
              'муниципальный', 'район', 'округ', 'городской', 'город',
              'зато', 'муниципальное', 'национальный', 'рабочий поселок',
              'поселок городского типа', 'поселение']:
        n = n.replace(w, '')
    n = re.sub(r'[«»"\'\-\(\)\s]', '', n)
    return n.strip()


def get_category_pages(main_html, region_code):
    """From main region page, discover category URLs and types."""
    lines = get_text_lines(main_html)
    categories = []  # (url, cat_type)
    
    for line in lines:
        if re.match(r'^\d{8}$', line) and line.startswith(region_code):
            code = line
            # Category header: XX?00000 where ? is the type digit
            if code[3:] == '00000' and code[2] in CATEGORY_TYPES:
                cat_type = CATEGORY_TYPES[code[2]]
                url = f"{BASE}/oktmo/{code}000.html"
                categories.append((url, cat_type, code))
    
    return categories


def fetch_region_data(region_code):
    """Fetch all official (name, type) pairs for a region."""
    all_entries = []
    
    # Main page
    main_url = f"{BASE}/oktmo/{region_code}000000000.html"
    main_html = fetch_page(main_url)
    if not main_html:
        return all_entries
    
    # Discover categories
    cats = get_category_pages(main_html, region_code)
    
    if not cats:
        # No sub-categories; extract directly from main page
        entries = extract_entries_from_category_page(main_html)
        for code, name in entries:
            all_entries.append((name, 'ГО'))
        return all_entries
    
    for cat_url, cat_type, cat_code in cats:
        cat_html = fetch_page(cat_url)
        if cat_html:
            entries = extract_entries_from_category_page(cat_html)
            for code, name in entries:
                all_entries.append((name, cat_type))
    
    return all_entries


def fetch_ao_data(region_name, parent_code):
    """Fetch data for autonomous okrugs.
    AO sections are at deeper levels within the parent region's ОКТМО tree.
    We need to find the correct section code first.
    """
    all_entries = []
    
    # Main page of parent region
    main_url = f"{BASE}/oktmo/{parent_code}000000000.html"
    main_html = fetch_page(main_url)
    if not main_html:
        return all_entries
    
    lines = get_text_lines(main_html)
    
    # Find section for this AO
    # Typical pattern: for Nenets AO in Arkhangelsk (11): section 11100000
    # For HMAO in Tyumen (71): section 71800000
    # For YANAO in Tyumen (71): section 71900000
    ao_section_code = None
    for i, line in enumerate(lines):
        if re.match(r'^\d{8}$', line) and line.startswith(parent_code):
            # Check if next line contains the AO name hint
            if i + 1 < len(lines):
                next_line = lines[i + 1].lower()
                if 'ненецк' in next_line and 'ненецкий' in region_name.lower():
                    ao_section_code = line
                    break
                if 'ханты' in next_line and 'ханты' in region_name.lower():
                    ao_section_code = line
                    break
                if 'ямало' in next_line and 'ямало' in region_name.lower():
                    ao_section_code = line
                    break
    
    if not ao_section_code:
        print(f"  Could not find AO section for {region_name} in parent {parent_code}")
        # Try hardcoded sections
        if 'Ненецкий' in region_name:
            ao_section_code = f'{parent_code}100000'
        elif 'Ханты' in region_name:
            ao_section_code = f'{parent_code}800000'
        elif 'Ямало' in region_name:
            ao_section_code = f'{parent_code}900000'
    
    if not ao_section_code:
        return all_entries
    
    print(f"  AO section: {ao_section_code}")
    
    # Fetch AO section page
    ao_url = f"{BASE}/oktmo/{ao_section_code}000.html"
    ao_html = fetch_page(ao_url)
    if not ao_html:
        return all_entries
    
    # Find sub-categories within AO
    ao_lines = get_text_lines(ao_html)
    sub_cats = []
    for line in ao_lines:
        if re.match(r'^\d{8}$', line) and line.startswith(ao_section_code[:3]):
            # Check if it's a sub-category (XX?Y0000 where Y is type digit)
            # The AO section codes are like 111, 718, 719
            # Sub-categories would be at the next level
            if line[3:] == '00000' and len(line) == 8:
                # This is the AO header itself, skip
                continue
            # Check for sub-type codes (5/6/7 at position 4 or 5)
            # For AO like 111XXXXX, sub-types are at 1115, 1116, 1117
            if line.endswith('0000') and not line.endswith('00000'):
                # Potential sub-category like 11150000, 11160000, 11170000
                type_digit = line[3]  # 4th digit
                if type_digit in CATEGORY_TYPES:
                    cat_type = CATEGORY_TYPES[type_digit]
                    sub_url = f"{BASE}/oktmo/{line}000.html"
                    sub_cats.append((sub_url, cat_type, line))
    
    if sub_cats:
        for sub_url, cat_type, sub_code in sub_cats:
            sub_html = fetch_page(sub_url)
            if sub_html:
                entries = extract_entries_from_category_page(sub_html)
                for code, name in entries:
                    all_entries.append((name, cat_type))
    else:
        # Try to extract directly from AO page
        entries = extract_entries_from_category_page(ao_html)
        for code, name in entries:
            all_entries.append((name, 'ГО'))
    
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
    is_ao = region_name in AUTONOMOUS_OKRUGS
    
    if is_ao:
        parent_code = AUTONOMOUS_OKRUGS[region_name]
    else:
        for code, name in REGION_CODE_MAP.items():
            if name == region_name:
                oktmo_code = code
                break
    
    if not oktmo_code and not is_ao:
        print(f"\n{region_name}: NO CODE - SKIP")
        continue
    
    # Fetch data
    if is_ao:
        print(f"\n{region_name} (AO in parent {parent_code}):")
        entries = fetch_ao_data(region_name, parent_code)
    else:
        print(f"\n{region_name} (code {oktmo_code}):")
        entries = fetch_region_data(oktmo_code)
    
    if not entries:
        print(f"  NO DATA FETCHED")
        continue
    
    # Build lookup: normalized_name -> full_official_name
    official_lookup = {}
    for raw_name, cat_type in entries:
        full = compose_name(raw_name, cat_type)
        norm = normalize(raw_name)
        if norm:
            official_lookup[norm] = full
    
    print(f"  ОКТМО: {len(official_lookup)} entries")
    
    # Get DB districts
    with ENGINE.connect() as c:
        db_districts = c.execute(text(
            "SELECT id, name FROM districts WHERE region_id = :rid ORDER BY name"
        ), {'rid': region_id}).fetchall()
    
    print(f"  DB: {len(db_districts)} districts")
    
    # Match and update
    fixes = []
    matched = 0
    unmatched = []
    
    for did, dname in db_districts:
        d_norm = normalize(dname)
        if d_norm in official_lookup:
            official = official_lookup[d_norm]
            matched += 1
            if official != dname:
                fixes.append((str(did), dname, official))
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
        if matched:
            print(f"  All {matched} matched, no changes")
    
    if unmatched:
        total_unmatched_db += len(unmatched)
        for n in unmatched[:5]:
            print(f"  UNMATCHED: {n}")
        if len(unmatched) > 5:
            print(f"  ... +{len(unmatched)-5} more")
    
    regions_done += 1

print(f"\n\n{'='*60}")
print(f"DONE! Regions: {regions_done}")
print(f"Matched: {total_matched}, Fixed: {total_fixed}")
print(f"Unmatched DB entries: {total_unmatched_db}")
