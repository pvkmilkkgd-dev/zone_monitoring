"""Detailed check of Altai Krai: ОКТМО vs DB"""
import sys, re, requests
from bs4 import BeautifulSoup
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)

# 1. What ОКТМО says
print("=== ОКТМО data for Алтайский край (code 01) ===")
resp = requests.get("https://okp-okpd.ru/oktmo.aspx?kod=01", timeout=30)
resp.encoding = 'windows-1251'
soup = BeautifulSoup(resp.text, 'html.parser')

oktmo_entries = []
for tr in soup.find_all('tr'):
    cells = tr.find_all('td')
    if len(cells) >= 2:
        code = cells[0].get_text(strip=True)
        name = cells[1].get_text(strip=True)
        if re.match(r'^\d{11}$', code):
            oktmo_entries.append((code, name))

print(f"Total ОКТМО entries: {len(oktmo_entries)}")

# Classify by type
mr = [e for e in oktmo_entries if 'муниципальный район' in e[1].lower()]
go = [e for e in oktmo_entries if 'город' in e[1].lower() and 'район' not in e[1].lower()]
zato = [e for e in oktmo_entries if 'зато' in e[1].lower()]
mo = [e for e in oktmo_entries if 'муниципальный округ' in e[1].lower()]
other = [e for e in oktmo_entries if e not in mr and e not in go and e not in zato and e not in mo]

print(f"\nBy type in ОКТМО:")
print(f"  Муниципальные районы: {len(mr)}")
print(f"  Города (городские округа): {len(go)}")
for g in go:
    print(f"    {g[0]} {g[1]}")
print(f"  ЗАТО: {len(zato)}")
for z in zato:
    print(f"    {z[0]} {z[1]}")
print(f"  Муниципальные округа: {len(mo)}")
for m in mo:
    print(f"    {m[0]} {m[1]}")
print(f"  Другое: {len(other)}")
for o in other:
    print(f"    {o[0]} {o[1]}")

# 2. What's in DB
print(f"\n\n=== DB data for Алтайский край ===")
with e.connect() as c:
    rows = c.execute(text("""
        SELECT d.name FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Алтайский край' ORDER BY d.name
    """)).fetchall()

print(f"Total DB districts: {len(rows)}")
db_mr = [r[0] for r in rows if 'муниципальный район' in r[0].lower()]
db_go = [r[0] for r in rows if 'городской округ' in r[0].lower()]
db_zato = [r[0] for r in rows if 'зато' in r[0].lower()]
db_mo = [r[0] for r in rows if 'муниципальный округ' in r[0].lower()]
db_other = [r[0] for r in rows if r[0] not in db_mr and r[0] not in db_go and r[0] not in db_zato and r[0] not in db_mo]

print(f"  Муниципальные районы: {len(db_mr)}")
print(f"  Городские округа: {len(db_go)}")
for g in db_go:
    print(f"    {g}")
print(f"  ЗАТО: {len(db_zato)}")
for z in db_zato:
    print(f"    {z}")
print(f"  Муниципальные округа: {len(db_mo)}")
for m in db_mo:
    print(f"    {m}")
print(f"  Без типа / другое: {len(db_other)}")
for o in db_other:
    print(f"    {o}")
