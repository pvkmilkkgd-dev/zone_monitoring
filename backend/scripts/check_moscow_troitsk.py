import sys, time, re, requests
from bs4 import BeautifulSoup

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
BASE = "https://classinform.ru"
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html', 'Accept-Language': 'ru-RU,ru;q=0.9'}

# 1. What's in DB for Moscow?
print("=== Москва в базе ===")
with ENGINE.connect() as c:
    rows = c.execute(text("""
        SELECT d.id, d.name, ROUND(ST_Area(d.geom::geography)/1e6) as area,
               ST_NPoints(d.geom) as pts
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name ILIKE '%Москва%' OR r.name ILIKE '%москов%'
        ORDER BY d.name
    """)).fetchall()
    print(f"  Найдено: {len(rows)} районов")
    for did, dname, area, pts in rows:
        print(f"  {dname} (area={area} km2, pts={pts})")
    
    # Check for Troitsk specifically
    troitsk = [r for r in rows if 'роиц' in r[1]]
    if troitsk:
        print(f"\n  Троицк найден: {troitsk}")
    else:
        print(f"\n  Троицк НЕ найден!")

# 2. Check ОКТМО for Moscow (code 45)
print("\n=== ОКТМО Москвы ===")
for cat_code, cat_type in [('45500000000', 'МО'), ('45600000000', 'МР'), ('45700000000', 'ГО'), ('45800000000', 'ВГТ'), ('45300000000', 'ВГТ2')]:
    time.sleep(1)
    resp = requests.get(f"{BASE}/oktmo/{cat_code}.html", headers=HEADERS, timeout=60)
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, 'html.parser')
        lines = [l.strip() for l in soup.get_text('\n', strip=True).split('\n') if l.strip()]
        troitsk_lines = []
        i = 0
        while i < len(lines):
            if 'роиц' in lines[i]:
                troitsk_lines.append(lines[i])
            i += 1
        if troitsk_lines:
            print(f"  {cat_type} ({cat_code}): {troitsk_lines}")
    elif resp.status_code == 404:
        pass  # category doesn't exist
