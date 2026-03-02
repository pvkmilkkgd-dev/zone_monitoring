"""Dry-run: test parsing for Altai Krai, Kaliningrad, Amur, KBR to verify correctness."""
import sys, os, re, time, requests
from bs4 import BeautifulSoup

os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)

BASE = "https://classinform.ru"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'ru-RU,ru;q=0.9',
}

CATEGORY_TYPES = {'5': 'МО', '6': 'МР', '7': 'ГО', '8': 'ВГТ'}


def fetch_page(url):
    for attempt in range(3):
        try:
            time.sleep(1.2)
            resp = requests.get(url, headers=HEADERS, timeout=60)
            if resp.status_code == 200:
                return resp.text
        except Exception as e:
            print(f"  ERR: {e}")
            time.sleep(3)
    return None


def get_text_lines(html):
    soup = BeautifulSoup(html, 'html.parser')
    body = soup.find('body')
    if not body:
        return []
    return [l.strip() for l in body.get_text('\n', strip=True).split('\n') if l.strip()]


def extract_entries(html):
    lines = get_text_lines(html)
    entries = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r'^\d{8}$', line):
            code = line
            # Skip category/section headers
            if code[3:] == '00000' or code[2:] == '000000':
                i += 1
                continue
            # Next meaningful line is the name
            j = i + 1
            while j < len(lines):
                candidate = lines[j]
                if candidate.startswith('(') and ('включен' in candidate.lower() or 'действует' in candidate.lower() or 'исключен' in candidate.lower()):
                    j += 1
                    continue
                if re.match(r'^\d{8}$', candidate):
                    break
                if 'Полная расшифровка' in candidate or 'ОКТМО' in candidate:
                    break
                name = re.sub(r'\s*\([^)]*\)\s*$', '', candidate).strip()
                if name and len(name) > 1 and not name[0].isdigit():
                    entries.append((code, name))
                break
            i = j if j > i + 1 else i + 1
        else:
            i += 1
    return entries


def has_type(name):
    lower = name.lower()
    return any(k in lower for k in [
        'муниципальный район', 'муниципальный округ', 'городской округ',
        'город ', 'зато ', 'муниципальное образование',
    ])


def is_adjective(name):
    word = name.split()[-1].lower() if name.split() else ''
    return any(word.endswith(e) for e in [
        'ский', 'ской', 'ная', 'ное', 'ный', 'кий', 'жий', 'ший', 'ний', 'тий',
    ])


def compose(name, cat_type):
    if has_type(name):
        return name
    if name.upper().startswith('ЗАТО'):
        return name
    if cat_type == 'МО':
        return f"{name} муниципальный округ" if is_adjective(name) else f"муниципальный округ {name}"
    elif cat_type == 'МР':
        return f"{name} муниципальный район" if is_adjective(name) else f"муниципальный район {name}"
    elif cat_type == 'ГО':
        if is_adjective(name):
            return f"{name} городской округ"
        return f"городской округ {name}"
    return name


# Test regions
TEST_REGIONS = [
    ('01', 'Алтайский край'),
    ('10', 'Амурская область'),
    ('27', 'Калининградская область'),
    ('83', 'КБР'),
    ('20', 'Воронежская область'),
]

for code, label in TEST_REGIONS:
    print(f"\n{'='*60}")
    print(f"=== {label} (code {code}) ===")
    
    main_html = fetch_page(f"{BASE}/oktmo/{code}000000000.html")
    if not main_html:
        print("  FAILED to fetch main page")
        continue
    
    # Find categories
    lines = get_text_lines(main_html)
    cats = []
    for line in lines:
        if re.match(r'^\d{8}$', line) and line.startswith(code):
            if line[3:] == '00000' and line[2] in CATEGORY_TYPES:
                cats.append((line, CATEGORY_TYPES[line[2]]))
    
    print(f"  Categories: {cats}")
    
    all_entries = []
    for cat_code, cat_type in cats:
        cat_url = f"{BASE}/oktmo/{cat_code}000.html"
        cat_html = fetch_page(cat_url)
        if cat_html:
            entries = extract_entries(cat_html)
            print(f"\n  --- {cat_type} ({cat_code}): {len(entries)} entries ---")
            for ecode, ename in entries:
                full = compose(ename, cat_type)
                marker = " [COMPOSED]" if full != ename else ""
                print(f"    {ecode} {ename} -> {full}{marker}")
                all_entries.append((ename, full, cat_type))
    
    print(f"\n  TOTAL: {len(all_entries)} entries")
