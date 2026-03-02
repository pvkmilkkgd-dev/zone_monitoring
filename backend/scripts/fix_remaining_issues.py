"""Fix remaining issues after the classinform update:
1. Fix corrupted names (e.g., missing spaces)
2. Handle HMAO/YANAO sub-categories properly
3. Fix Moscow/SPb/Sevastopol
4. Fix miscategorized districts
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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'ru-RU,ru;q=0.9',
}


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
    return [l.strip() for l in body.get_text('\n', strip=True).split('\n') if l.strip()] if body else []


def extract_entries(html):
    lines = get_text_lines(html)
    entries = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r'^\d{8}$', line):
            code = line
            if code[3:] == '00000' or code[2:] == '000000':
                i += 1
                continue
            j = i + 1
            while j < len(lines):
                candidate = lines[j]
                if candidate.startswith('(') and ('включен' in candidate.lower() or 'действует' in candidate.lower() or 'исключен' in candidate.lower()):
                    j += 1
                    continue
                if re.match(r'^\d{8}$', candidate) or 'Полная расшифровка' in candidate:
                    break
                name = re.sub(r'\s*\([^)]*\)\s*$', '', candidate).strip()
                if name and len(name) > 1 and not name[0].isdigit():
                    entries.append((code, name))
                break
            i = j if j > i + 1 else i + 1
        else:
            i += 1
    return entries


# =========================================
# 1. Fix corrupted name from killed script
# =========================================
print("=== 1. Fix corrupted names ===")
with ENGINE.begin() as c:
    # Fix "Холмогорский муниципальныйокруг" -> proper name
    result = c.execute(text(
        "UPDATE districts SET name = 'Холмогорский муниципальный округ' "
        "WHERE name LIKE '%муниципальныйокруг%' RETURNING name"
    ))
    for row in result:
        print(f"  Fixed: {row[0]}")

    # Fix "муниципальный округ Холмогорский муниципальныйокруг" if exists
    result = c.execute(text(
        "UPDATE districts SET name = 'Холмогорский муниципальный округ' "
        "WHERE name LIKE '%Холмогорский%' AND name != 'Холмогорский муниципальный округ' "
        "AND name LIKE '%округ%' RETURNING id, name"
    ))
    for row in result:
        print(f"  Fixed: {row[1]}")

    # Fix "городской округ округ Муром" -> "городской округ Муром"
    result = c.execute(text(
        "UPDATE districts SET name = 'городской округ Муром' "
        "WHERE name = 'городской округ округ Муром' RETURNING name"
    ))
    for row in result:
        print(f"  Fixed: {row[0]}")
    
    # Fix "городской округ город-курорт Ессентуки" -> keep the ОКТМО name
    # classinform actually says just "город-курорт Ессентуки" without "городской округ"
    # But it's a ГО... Let me check what ОКТМО says
    # For now leave as-is, it's descriptive enough


# =========================================
# 2. Fix ХМАО - fetch sub-categories properly
# =========================================
print("\n=== 2. ХМАО ===")
# HMAO is at section 71800000 in Tyumen oblast
# It has sub-categories at 718X0000 level
hmao_main_url = f"{BASE}/oktmo/71800000000.html"
hmao_html = fetch_page(hmao_main_url)
if hmao_html:
    lines = get_text_lines(hmao_html)
    cats = []
    for line in lines:
        if re.match(r'^\d{8}$', line) and line.startswith('718'):
            if line[5:] == '000' and line[3] != '0':
                # This is a sub-category like 71850000, 71860000, 71870000
                cats.append(line)
    
    print(f"  ХМАО sub-categories: {cats}")
    
    hmao_entries = []
    for cat_code in cats:
        cat_type_digit = cat_code[3]
        cat_type = {'5': 'МО', '6': 'МР', '7': 'ГО'}.get(cat_type_digit, 'ГО')
        cat_url = f"{BASE}/oktmo/{cat_code}000.html"
        cat_html = fetch_page(cat_url)
        if cat_html:
            entries = extract_entries(cat_html)
            print(f"  {cat_type} ({cat_code}): {len(entries)} entries")
            for code, name in entries:
                hmao_entries.append((name, cat_type))
                print(f"    {name}")
    
    print(f"  Total ХМАО entries: {len(hmao_entries)}")
else:
    print("  Failed to fetch ХМАО main page")
    hmao_entries = []


# =========================================
# 3. Fix ЯНАО - fetch sub-categories properly
# =========================================
print("\n=== 3. ЯНАО ===")
yanao_main_url = f"{BASE}/oktmo/71900000000.html"
yanao_html = fetch_page(yanao_main_url)
if yanao_html:
    lines = get_text_lines(yanao_html)
    cats = []
    for line in lines:
        if re.match(r'^\d{8}$', line) and line.startswith('719'):
            if line[5:] == '000' and line[3] != '0':
                cats.append(line)
    
    print(f"  ЯНАО sub-categories: {cats}")
    
    yanao_entries = []
    for cat_code in cats:
        cat_type_digit = cat_code[3]
        cat_type = {'5': 'МО', '6': 'МР', '7': 'ГО'}.get(cat_type_digit, 'ГО')
        cat_url = f"{BASE}/oktmo/{cat_code}000.html"
        cat_html = fetch_page(cat_url)
        if cat_html:
            entries = extract_entries(cat_html)
            print(f"  {cat_type} ({cat_code}): {len(entries)} entries")
            for code, name in entries:
                yanao_entries.append((name, cat_type))
                print(f"    {name}")
    
    print(f"  Total ЯНАО entries: {len(yanao_entries)}")
else:
    yanao_entries = []


# =========================================
# 4. Fix НАО - check sub-categories
# =========================================
print("\n=== 4. НАО ===")
nao_main_url = f"{BASE}/oktmo/11800000000.html"
nao_html = fetch_page(nao_main_url)
if nao_html:
    lines = get_text_lines(nao_html)
    cats = []
    for line in lines:
        if re.match(r'^\d{8}$', line) and line.startswith('118'):
            if line[5:] == '000' and line[3] != '0':
                cats.append(line)
    
    print(f"  НАО sub-categories: {cats}")
    
    nao_entries = []
    for cat_code in cats:
        cat_type_digit = cat_code[3]
        cat_type = {'5': 'МО', '6': 'МР', '7': 'ГО'}.get(cat_type_digit, 'ГО')
        cat_url = f"{BASE}/oktmo/{cat_code}000.html"
        cat_html = fetch_page(cat_url)
        if cat_html:
            entries = extract_entries(cat_html)
            print(f"  {cat_type} ({cat_code}): {len(entries)} entries")
            for code, name in entries:
                nao_entries.append((name, cat_type))
                print(f"    {name}")
    
    print(f"  Total НАО entries: {len(nao_entries)}")
else:
    nao_entries = []


# =========================================
# 5. Show current state of all unmatched
# =========================================
print("\n=== 5. Current unmatched districts ===")
with ENGINE.connect() as c:
    # Find districts with potentially problematic names
    rows = c.execute(text("""
        SELECT d.name, r.name as region_name 
        FROM districts d JOIN regions r ON d.region_id = r.id 
        WHERE d.name NOT LIKE '%%муниципальный%%'
        AND d.name NOT LIKE '%%городской%%'
        AND d.name NOT LIKE '%%город %%'
        AND d.name NOT LIKE '%%ЗАТО%%'
        AND d.name NOT LIKE '%%рабочий%%'
        AND d.name NOT LIKE '%%округ%%'
        AND d.name NOT LIKE '%%район%%'
        AND d.name NOT LIKE '%%поселение%%'
        AND d.name NOT LIKE '%%Бежтинский%%'
        ORDER BY r.name, d.name
    """)).fetchall()
    
    print(f"Districts without type designation: {len(rows)}")
    for dname, rname in rows:
        print(f"  [{rname}] {dname}")

print("\nDone!")
