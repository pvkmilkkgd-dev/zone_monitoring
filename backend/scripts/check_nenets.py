import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    # Get Nenets info
    r = c.execute(text(
        "SELECT id, name, ST_Area(geom::geography)/1e6, ST_NPoints(geom) "
        "FROM regions WHERE name LIKE '%Ненец%'"
    )).fetchone()
    print(f"Region: {r[1]}")
    print(f"Area: {r[2]:.0f} km2, Points: {r[3]}")
    rid = str(r[0])
    
    # Districts
    rows = c.execute(text(
        "SELECT name, ST_Area(geom::geography)/1e6, ST_NPoints(geom), "
        "ST_AsText(ST_Centroid(geom)), "
        "ST_YMin(geom), ST_YMax(geom) "
        "FROM districts WHERE region_id = :rid ORDER BY name"
    ), {"rid": rid}).fetchall()
    
    print(f"\nDistricts: {len(rows)}")
    total = 0
    for name, area, pts, centroid, ymin, ymax in rows:
        print(f"  {area:>10.0f} km2  {pts:>5d} pts  lat {ymin:.1f}-{ymax:.1f}  {name}")
        total += area
    
    print(f"\nTotal district area: {total:.0f} km2")
    print(f"Region area: {r[2]:.0f} km2")
    print(f"Coverage: {total/r[2]*100:.1f}%")

# What ОКТМО says
import requests, re
from bs4 import BeautifulSoup
print("\n=== ОКТМО ===")
resp = requests.get("https://okp-okpd.ru/oktmo.aspx?kod=11", timeout=30)
resp.encoding = 'windows-1251'
soup = BeautifulSoup(resp.text, 'html.parser')
for tr in soup.find_all('tr'):
    cells = tr.find_all('td')
    if len(cells) >= 2:
        code = cells[0].get_text(strip=True)
        name = cells[1].get_text(strip=True)
        if re.match(r'^\d{11}$', code) and 'ненец' in name.lower():
            print(f"  {code} {name}")

# Also check NAO-specific ОКТМО code
print("\n=== ОКТМО код 11100 (НАО) ===")
resp2 = requests.get("https://okp-okpd.ru/oktmo.aspx?kod=11100", timeout=30)
resp2.encoding = 'windows-1251'
soup2 = BeautifulSoup(resp2.text, 'html.parser')
for tr in soup2.find_all('tr'):
    cells = tr.find_all('td')
    if len(cells) >= 2:
        code = cells[0].get_text(strip=True)
        name = cells[1].get_text(strip=True)
        if re.match(r'^\d{11}$', code):
            print(f"  {code} {name}")
