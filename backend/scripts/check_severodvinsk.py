import sys, time, re, requests
from bs4 import BeautifulSoup

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
BASE = "https://classinform.ru"
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html', 'Accept-Language': 'ru-RU,ru;q=0.9'}

# 1. What's in DB?
print("=== В базе (Архангельская область, Северодвинск) ===")
with ENGINE.connect() as c:
    rows = c.execute(text("""
        SELECT d.id, d.name, ROUND(ST_Area(d.geom::geography)/1e6) as area
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Архангельская область' AND d.name ILIKE '%еверодвинск%'
    """)).fetchall()
    for did, dname, area in rows:
        print(f"  '{dname}' id={did} area={area} km2")

# 2. Check ОКТМО for Arkhangelsk (code 11)
print("\n=== ОКТМО Архангельской области ===")
for cat_code, cat_type in [('11500000000', 'МО'), ('11600000000', 'МР'), ('11700000000', 'ГО')]:
    time.sleep(1)
    resp = requests.get(f"{BASE}/oktmo/{cat_code}.html", headers=HEADERS, timeout=60)
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, 'html.parser')
        lines = [l.strip() for l in soup.get_text('\n', strip=True).split('\n') if l.strip()]
        i = 0
        while i < len(lines):
            if re.match(r'^\d{8}$', lines[i]) and lines[i].startswith('11') and lines[i][3:] != '00000':
                if i+1 < len(lines) and 'еверодвинск' in lines[i+1]:
                    name = re.sub(r'\s*\([^)]*\)\s*$', '', lines[i+1]).strip()
                    print(f"  {cat_type}: code={lines[i]} name='{name}'")
            i += 1

# 3. Also show all entries with unusual quotes in names
print("\n=== Записи с кавычками в названиях (вся база) ===")
with ENGINE.connect() as c:
    rows = c.execute(text("""
        SELECT d.name, r.name FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE d.name LIKE '%"%' OR d.name LIKE '%«%'
        ORDER BY r.name, d.name
    """)).fetchall()
    for dname, rname in rows:
        print(f"  [{rname}] {dname}")
