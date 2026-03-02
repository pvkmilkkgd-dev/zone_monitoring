"""
Clean up Arkhangelsk Oblast - remove Bashkortostan entries that got mixed in.
Keep only the correct 26 Arkhangelsk districts that are in ОКТМО.
"""
import sys, re, requests
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings
from bs4 import BeautifulSoup

ENGINE = create_engine(settings.DATABASE_URL)

# Get ОКТМО names for Arkhangelsk (code 11)
resp = requests.get("https://okp-okpd.ru/oktmo.aspx?kod=11", timeout=30)
resp.encoding = 'windows-1251'
soup = BeautifulSoup(resp.text, 'html.parser')

oktmo_raw = []
for tr in soup.find_all('tr'):
    cells = tr.find_all('td')
    if len(cells) >= 2:
        code_text = cells[0].get_text(strip=True)
        name_text = cells[1].get_text(strip=True)
        if re.match(r'^\d{11}$', code_text):
            if 'ненец' not in name_text.lower():
                oktmo_raw.append(name_text)

def normalize(name):
    n = name.strip().lower()
    for w in ['муниципальный район', 'муниципальный округ', 'городской округ',
              'район', 'округ', 'городской', 'город', 'зато', 'муниципальный',
              'муниципальное образование']:
        n = n.replace(w, '')
    n = n.replace('ё', 'е').replace('-', '').replace(' ', '').replace('«', '').replace('»', '')
    return n

oktmo_norms = set(normalize(n) for n in oktmo_raw)
print(f"ОКТМО names ({len(oktmo_norms)}):")
for n in sorted(oktmo_raw):
    print(f"  {n} -> {normalize(n)}")

# Get current districts
with ENGINE.connect() as c:
    rid = str(c.execute(text(
        "SELECT id FROM regions WHERE name = 'Архангельская область'"
    )).fetchone()[0])
    
    rows = c.execute(text(
        "SELECT id, name FROM districts WHERE region_id = :rid ORDER BY name"
    ), {"rid": rid}).fetchall()

print(f"\nCurrent districts: {len(rows)}")
to_delete = []
to_keep = []
for did, name in rows:
    nn = normalize(name)
    if nn in oktmo_norms:
        to_keep.append(name)
    else:
        to_delete.append((str(did), name))
        print(f"  DELETE: {name} (norm: {nn})")

for name in to_keep:
    print(f"  KEEP: {name}")

if to_delete:
    print(f"\nDeleting {len(to_delete)} entries...")
    with ENGINE.connect() as c:
        for did, name in to_delete:
            c.execute(text("DELETE FROM districts WHERE id = :id"), {"id": did})
        c.commit()
    print("Done!")

# Also check Bashkortostan wasn't damaged
with ENGINE.connect() as c:
    bash = c.execute(text(
        "SELECT COUNT(id), COUNT(geom) FROM districts WHERE region_id = "
        "(SELECT id FROM regions WHERE name = 'Республика Башкортостан')"
    )).fetchone()
    print(f"\nБашкортостан: {bash[0]} districts, {bash[1]} with geometry")

# Final Arkhangelsk state
with ENGINE.connect() as c:
    rows = c.execute(text(
        "SELECT name, ST_Area(geom::geography)/1e6 "
        "FROM districts WHERE region_id = :rid ORDER BY name"
    ), {"rid": rid}).fetchall()
    total = sum(r[1] for r in rows)
    rarea = c.execute(text(
        "SELECT ST_Area(geom::geography)/1e6 FROM regions WHERE id = :rid"
    ), {"rid": rid}).fetchone()[0]

print(f"\nАрхангельская область: {len(rows)} districts")
for name, area in rows:
    print(f"  {area:>10.0f} km2  {name}")
print(f"\nTotal: {total:.0f} km2, Region: {rarea:.0f} km2, Coverage: {total/rarea*100:.1f}%")

# Overall
with ENGINE.connect() as c:
    stats = c.execute(text("SELECT COUNT(id), COUNT(geom) FROM districts")).fetchone()
print(f"Overall: {stats[0]} districts, {stats[1]} with geometry")
