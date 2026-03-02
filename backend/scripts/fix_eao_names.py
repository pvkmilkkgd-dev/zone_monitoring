"""Quick fix: rename EAO districts to ОКТМО names."""
import sys, os, re, requests
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings
from bs4 import BeautifulSoup

ENGINE = create_engine(settings.DATABASE_URL)

def normalize(name):
    n = name.strip().lower()
    for w in ['муниципальный район', 'муниципальный округ', 'городской округ',
              'район', 'округ', 'городской', 'город', 'зато', 'муниципальный']:
        n = n.replace(w, '')
    n = n.replace('ё', 'е').replace('-', '').replace(' ', '').replace('«', '').replace('»', '')
    return n

def transform_name(name):
    m = re.match(r'^город\s+(.+)$', name)
    if m:
        return f"городской округ {m.group(1)}"
    return name

with ENGINE.connect() as conn:
    row = conn.execute(text("SELECT id FROM regions WHERE name = :n"),
                       {"n": "Еврейская автономная область"}).fetchone()
    region_id = str(row[0])
    
    rows = conn.execute(text("SELECT id, name FROM districts WHERE region_id = :rid"),
                        {"rid": region_id}).fetchall()

db_by_norm = {normalize(n): (str(did), n) for did, n in rows}

# Fetch ОКТМО
resp = requests.get("https://okp-okpd.ru/oktmo.aspx?kod=99", timeout=30)
resp.encoding = 'windows-1251'
soup = BeautifulSoup(resp.text, 'html.parser')
oktmo_names = []
for tr in soup.find_all('tr'):
    cells = tr.find_all('td')
    if len(cells) >= 2:
        code_text = cells[0].get_text(strip=True)
        name_text = cells[1].get_text(strip=True)
        if re.match(r'^\d{11}$', code_text):
            oktmo_names.append(transform_name(name_text))

print(f"ОКТМО names for EAO ({len(oktmo_names)}):")
for n in oktmo_names:
    print(f"  {n}")

renames = 0
for target in oktmo_names:
    tnorm = normalize(target)
    if tnorm in db_by_norm:
        did, dname = db_by_norm[tnorm]
        if dname != target:
            with ENGINE.connect() as conn:
                conn.execute(text("UPDATE districts SET name = :n WHERE id = :id"),
                           {"n": target, "id": did})
                conn.commit()
            print(f"  Renamed: {dname} -> {target}")
            renames += 1

print(f"\nRenamed: {renames}")

with ENGINE.connect() as conn:
    final = conn.execute(text("SELECT name FROM districts WHERE region_id = :rid ORDER BY name"),
                        {"rid": region_id}).fetchall()
print("\nFinal names:")
for (n,) in final:
    print(f"  {n}")
