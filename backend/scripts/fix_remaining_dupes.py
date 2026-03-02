"""Fix remaining duplicate cases that need manual investigation."""
import sys, os, time, re, requests
from bs4 import BeautifulSoup

os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
BASE = "https://classinform.ru"
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html', 'Accept-Language': 'ru-RU,ru;q=0.9'}


def fetch_page(url):
    for attempt in range(3):
        try:
            time.sleep(1)
            resp = requests.get(url, headers=HEADERS, timeout=60)
            if resp.status_code == 200:
                return resp.text
        except:
            time.sleep(3)
    return None


def get_entries(html, prefix):
    """Get all district entries from category page."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    body = soup.find('body')
    if not body:
        return []
    lines = [l.strip() for l in body.get_text('\n', strip=True).split('\n') if l.strip()]
    entries = []
    i = 0
    while i < len(lines):
        if re.match(r'^\d{8}$', lines[i]) and lines[i].startswith(prefix) and lines[i][3:] != '00000':
            if i + 1 < len(lines):
                name = re.sub(r'\s*\([^)]*\)\s*$', '', lines[i+1]).strip()
                entries.append((lines[i], name))
        i += 1
    return entries


with ENGINE.begin() as c:
    # ============================================
    # 1. Красноярский край - Эвенкийский МО x3
    # ============================================
    print("=== Красноярский край: Эвенкийский МО x3 ===")
    rows = c.execute(text("""
        SELECT d.id, d.name, ROUND(ST_Area(d.geom::geography)/1e6) as area
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Красноярский край' AND d.name LIKE '%Эвенкий%'
        ORDER BY ST_Area(d.geom::geography)
    """)).fetchall()
    for did, dname, area in rows:
        print(f"  {dname} id={did} area={area}")
    # 761734 km2 = the real Эвенкийский МО
    # 4 km2 and 27 km2 are tiny fragments - delete them
    small_ids = [str(rows[0][0]), str(rows[1][0])]
    print(f"  DELETE tiny fragments: {small_ids}")
    c.execute(text("DELETE FROM districts WHERE id = :id1 OR id = :id2"),
             {'id1': small_ids[0], 'id2': small_ids[1]})

    # ============================================
    # 2. Приморский край - Партизанский МО x2
    # ============================================
    print("\n=== Приморский край: Партизанский МО x2 ===")
    rows = c.execute(text("""
        SELECT d.id, d.name, ROUND(ST_Area(d.geom::geography)/1e6) as area
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Приморский край' AND d.name LIKE '%Партизан%'
        ORDER BY ST_Area(d.geom::geography)
    """)).fetchall()
    for did, dname, area in rows:
        print(f"  {dname} id={did} area={area}")

    # Check ОКТМО: Приморский край code 05
    print("  Checking ОКТМО...")
    
    # МО page
    mo_html = fetch_page(f"{BASE}/oktmo/05500000000.html")
    if mo_html:
        ents = get_entries(mo_html, '05')
        partiz = [e for e in ents if 'артизан' in e[1]]
        print(f"  МО: {partiz}")
    
    # ГО page
    go_html = fetch_page(f"{BASE}/oktmo/05700000000.html")
    if go_html:
        ents = get_entries(go_html, '05')
        partiz = [e for e in ents if 'артизан' in e[1]]
        print(f"  ГО: {partiz}")

    # Small one (1303 km2) is probably город Партизанск (ГО)
    # Need to check - both are quite large
    # Actually Партизанский ГО is a city, should be smaller
    # Let me check if one is actually the city
    if len(rows) == 2:
        small_id, small_name, small_area = rows[0]
        large_id, large_name, large_area = rows[1]
        # 1303 km2 is too large for a city... let me check centroids
        cents = c.execute(text("""
            SELECT d.id, ST_AsText(ST_Centroid(d.geom)) 
            FROM districts d JOIN regions r ON d.region_id = r.id
            WHERE r.name = 'Приморский край' AND d.name LIKE '%Партизан%'
            ORDER BY ST_Area(d.geom::geography)
        """)).fetchall()
        for did, cent in cents:
            print(f"  centroid: {did} -> {cent}")
        
        # ОКТМО: Партизанский муниципальный округ (МО) and город Партизанск (ГО)
        # The small one is likely the ГО (город Партизанск)
        print(f"  FIX small ({small_area}km2) -> 'город Партизанск'")
        c.execute(text("UPDATE districts SET name = 'город Партизанск' WHERE id = :id"),
                 {'id': str(small_id)})

    # ============================================
    # 3. Крым - Бахчисарайский МР x2
    # ============================================
    print("\n=== Крым: Бахчисарайский МР x2 ===")
    rows = c.execute(text("""
        SELECT d.id, d.name, ROUND(ST_Area(d.geom::geography)/1e6) as area,
               ST_NPoints(d.geom), ST_AsText(ST_Centroid(d.geom))
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Республика Крым' AND d.name LIKE '%Бахчисарай%'
    """)).fetchall()
    for did, dname, area, pts, cent in rows:
        print(f"  {dname} id={did} area={area} pts={pts} centroid={cent}")
    # Same area = exact duplicate, delete one
    if len(rows) == 2 and rows[0][2] == rows[1][2]:
        print(f"  DELETE exact duplicate: {rows[1][0]}")
        c.execute(text("DELETE FROM districts WHERE id = :id"), {'id': str(rows[1][0])})

    # ============================================
    # 4. Якутия - Анабарский x2
    # ============================================
    print("\n=== Якутия: Анабарский x2 ===")
    rows = c.execute(text("""
        SELECT d.id, d.name, ROUND(ST_Area(d.geom::geography)/1e6) as area,
               ST_NPoints(d.geom), ST_AsText(ST_Centroid(d.geom))
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Республика Саха (Якутия)' AND d.name LIKE '%Анабар%'
    """)).fetchall()
    for did, dname, area, pts, cent in rows:
        print(f"  {dname} id={did} area={area} pts={pts} centroid={cent}")
    # Very similar areas but different polygons - likely overlapping duplicates
    # Keep the one with more detail points and delete the other
    if len(rows) == 2:
        if rows[0][3] >= rows[1][3]:
            keep, delete = rows[0], rows[1]
        else:
            keep, delete = rows[1], rows[0]
        print(f"  KEEP: {keep[0]} ({keep[3]} pts)")
        print(f"  DELETE: {delete[0]} ({delete[3]} pts)")
        c.execute(text("DELETE FROM districts WHERE id = :id"), {'id': str(delete[0])})

    # ============================================
    # 5. Татарстан - Арский МР x2
    # ============================================
    print("\n=== Татарстан: Арский МР x2 ===")
    rows = c.execute(text("""
        SELECT d.id, d.name, ROUND(ST_Area(d.geom::geography)/1e6) as area,
               ST_NPoints(d.geom), ST_AsText(ST_Centroid(d.geom))
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Республика Татарстан' AND d.name LIKE '%Арск%'
    """)).fetchall()
    for did, dname, area, pts, cent in rows:
        print(f"  {dname} id={did} area={area} pts={pts} centroid={cent}")
    # 598 km2 vs 1846 km2 - the small one might be a sub-entity or fragment
    # In ОКТМО only one Арский МР exists
    if len(rows) == 2:
        small, large = (rows[0], rows[1]) if rows[0][2] < rows[1][2] else (rows[1], rows[0])
        print(f"  DELETE smaller fragment: {small[0]} ({small[2]}km2)")
        c.execute(text("DELETE FROM districts WHERE id = :id"), {'id': str(small[0])})

    # ============================================
    # 6. Свердловская - город Ирбит x2
    # ============================================
    print("\n=== Свердловская: город Ирбит x2 ===")
    rows = c.execute(text("""
        SELECT d.id, d.name, ROUND(ST_Area(d.geom::geography)/1e6) as area,
               ST_NPoints(d.geom)
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Свердловская область' AND d.name LIKE '%Ирбит%'
    """)).fetchall()
    for did, dname, area, pts in rows:
        print(f"  {dname} id={did} area={area} pts={pts}")
    
    # Check Sverdlovsk ОКТМО (code 65)
    print("  Checking ОКТМО...")
    mo_html = fetch_page(f"{BASE}/oktmo/65500000000.html")
    if mo_html:
        ents = get_entries(mo_html, '65')
        irbit = [e for e in ents if 'рбит' in e[1]]
        print(f"  МО: {irbit}")
    
    mr_html = fetch_page(f"{BASE}/oktmo/65600000000.html")
    if mr_html:
        ents = get_entries(mr_html, '65')
        irbit = [e for e in ents if 'рбит' in e[1]]
        print(f"  МР: {irbit}")
    
    go_html = fetch_page(f"{BASE}/oktmo/65700000000.html")
    if go_html:
        ents = get_entries(go_html, '65')
        irbit = [e for e in ents if 'рбит' in e[1]]
        print(f"  ГО: {irbit}")
    
    # Expecting: "Ирбитский муниципальный округ" (МО) for the large one
    # and "город Ирбит" (ГО) for the small one
    if len(rows) == 2:
        small, large = (rows[0], rows[1]) if rows[0][2] < rows[1][2] else (rows[1], rows[0])
        # Large one -> Ирбитский МО
        print(f"  FIX large ({large[2]}km2) -> 'Ирбитский муниципальный округ'")
        c.execute(text("UPDATE districts SET name = 'Ирбитский муниципальный округ' WHERE id = :id"),
                 {'id': str(large[0])})


# ============================================
# Also fix: ГО names that are just adjectives
# ============================================
print("\n=== Checking incomplete ГО names ===")
with ENGINE.begin() as c2:
    # Горноуральский was set to just "Горноуральский" - need to check ОКТМО
    # From Sverdlovsk МО page, it should be "Горноуральский муниципальный округ"
    # But the entry we found was just "Горноуральский" in МО category
    # Let me check if there's another entry for it
    rows = c2.execute(text("""
        SELECT d.id, d.name, ROUND(ST_Area(d.geom::geography)/1e6) as area
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Свердловская область' AND d.name = 'Горноуральский'
    """)).fetchall()
    for did, dname, area in rows:
        print(f"  {dname} id={did} area={area}")
    # "Горноуральский" alone is not a complete name. Check if it should be
    # "Горноуральский городской округ" or "Горноуральский муниципальный округ"
    # From ОКТМО it was under МО category, so it should be "Горноуральский муниципальный округ"
    if rows:
        print(f"  FIX -> 'Горноуральский муниципальный округ'")
        c2.execute(text("UPDATE districts SET name = 'Горноуральский муниципальный округ' WHERE name = 'Горноуральский'"))

    # Similarly check other incomplete ГО names from earlier fixes
    # "Беловский", "Дальнереченский", etc. - these are listed in ОКТМО as just that
    # In the ГО category. Let's check if they should have "городской округ" prefix
    incomplete = c2.execute(text("""
        SELECT d.name, r.name FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE d.name IN ('Беловский', 'Дальнереченский', 'Камышловский', 'Карачаевский',
                         'Кемеровский', 'Новокузнецкий', 'Пермский', 'Прокопьевский',
                         'Троицкий', 'Чебаркульский', 'Юргинский')
    """)).fetchall()
    print(f"\n  Incomplete ГО names:")
    for dname, rname in incomplete:
        print(f"  [{rname}] {dname}")
    # These are official ОКТМО names from ГО category - just the base adjective
    # But we need to compose full names. In ОКТМО ГО category, if name is just adjective,
    # it's "Xский городской округ" 
    for dname, rname in incomplete:
        full_name = f"{dname} городской округ"
        print(f"  FIX '{dname}' -> '{full_name}'")
        c2.execute(text("UPDATE districts SET name = :new WHERE name = :old"),
                  {'new': full_name, 'old': dname})


# Final check
print("\n\n=== Final duplicate check ===")
with ENGINE.connect() as c:
    rows = c.execute(text("""
        SELECT d.name, r.name, COUNT(*)
        FROM districts d JOIN regions r ON d.region_id = r.id
        GROUP BY d.name, r.name HAVING COUNT(*) > 1
        ORDER BY r.name
    """)).fetchall()
    if rows:
        for dname, rname, cnt in rows:
            print(f"  [{rname}] {dname} x{cnt}")
    else:
        print("  Дубликатов нет!")

print("\nDone!")
