"""Check Moscow city districts and ОКТМО structure."""
import sys, time, re, requests
from bs4 import BeautifulSoup

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
BASE = "https://classinform.ru"
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html', 'Accept-Language': 'ru-RU,ru;q=0.9'}

# 1. Regions containing "Москва"
print("=== Регионы (Москва) ===")
with ENGINE.connect() as c:
    rows = c.execute(text("""
        SELECT id, name FROM regions WHERE name ILIKE '%москва%' ORDER BY name
    """)).fetchall()
    for rid, rname in rows:
        cnt = c.execute(text("SELECT COUNT(*) FROM districts WHERE region_id = :id"), {'id': str(rid)}).scalar()
        print(f"  {rname} (id={rid}) — районов: {cnt}")

# 2. Districts of Moscow CITY (not oblast) - region name exactly "Москва" or "город Москва"?
with ENGINE.connect() as c:
    r = c.execute(text("SELECT id, name FROM regions WHERE name = 'Москва'")).fetchone()
    if not r:
        r = c.execute(text("SELECT id, name FROM regions WHERE name ILIKE 'город%москва%'")).fetchone()
    if not r:
        # try any that's not oblast
        r = c.execute(text("SELECT id, name FROM regions WHERE name ILIKE '%москва%' AND name NOT ILIKE '%область%'")).fetchone()
    if r:
        reg_id, reg_name = r
        print(f"\n=== Районы региона «{reg_name}» (id={reg_id}) ===")
        rows = c.execute(text("""
            SELECT d.id, d.name, ST_NPoints(d.geom) as pts,
                   ROUND(ST_Area(d.geom::geography)/1e6) as area_km2
            FROM districts d WHERE d.region_id = :rid
            ORDER BY d.name
        """), {'rid': str(reg_id)}).fetchall()
        print(f"  Всего: {len(rows)}")
        for did, dname, pts, area in rows:
            geom_ok = "OK" if (pts or 0) > 0 else "НЕТ ГЕОМЕТРИИ"
            print(f"  {dname}  pts={pts} area={area} km2  [{geom_ok}]")
    else:
        print("\n  Регион «Москва» (город) не найден.")

# 3. ОКТМО: Москва = code 45. What categories?
print("\n=== ОКТМО Москвы (код 45) — структура ===")
for code in ['45']:
    time.sleep(1)
    resp = requests.get(f"{BASE}/oktmo/{code}000000000.html", headers=HEADERS, timeout=60)
    if resp.status_code != 200:
        print(f"  {code}: HTTP {resp.status_code}")
        continue
    soup = BeautifulSoup(resp.text, 'html.parser')
    text = soup.get_text('\n', strip=True)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    # Find subcategory links 45X00000000
    for i, line in enumerate(lines):
        if re.match(r'^45[0-9]00000000$', line):
            print(f"  Категория: {line}")
            if i + 1 < len(lines):
                print(f"    -> {lines[i+1][:80]}")

# 4. List all Moscow entries from ОКТМО (ГО and other)
print("\n=== ОКТМО Москвы — городские округа (457) ===")
time.sleep(1)
resp = requests.get(f"{BASE}/oktmo/45700000000.html", headers=HEADERS, timeout=60)
if resp.status_code == 200:
    soup = BeautifulSoup(resp.text, 'html.parser')
    lines = [l.strip() for l in soup.get_text('\n', strip=True).split('\n') if l.strip()]
    n = 0
    for i in range(len(lines)):
        if re.match(r'^45[0-9]{6}$', lines[i]) and lines[i][3:6] != '000':
            if i+1 < len(lines):
                name = re.sub(r'\s*\([^)]*\)\s*$', '', lines[i+1]).strip()
                if name:
                    n += 1
                    print(f"  {lines[i]} {name}")
    print(f"  Всего ГО в ОКТМО: {n}")

print("\n=== ОКТМО Москвы — внутригородские территории (453, 458) ===")
for sub in ['453', '458']:
    time.sleep(1)
    resp = requests.get(f"{BASE}/oktmo/{sub}00000000.html", headers=HEADERS, timeout=60)
    if resp.status_code != 200:
        continue
    soup = BeautifulSoup(resp.text, 'html.parser')
    lines = [l.strip() for l in soup.get_text('\n', strip=True).split('\n') if l.strip()]
    print(f"  --- {sub} ---")
    for i in range(min(len(lines), 50)):
        if re.match(r'^45[0-9]{6}$', lines[i]) and lines[i][3:6] != '000':
            if i+1 < len(lines):
                print(f"  {lines[i]} {lines[i+1][:70]}")
