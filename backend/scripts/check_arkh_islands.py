"""Check all Arkhangelsk Oblast districts for island-like low-quality geometry"""
import sys, json, requests, time
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

with e.connect() as c:
    rows = c.execute(text("""
        SELECT d.id, d.name, ST_NPoints(d.geom), ST_NumGeometries(d.geom),
               ST_Area(d.geom::geography)/1e6,
               ST_YMin(d.geom), ST_YMax(d.geom),
               ST_XMin(d.geom), ST_XMax(d.geom)
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Архангельская область'
        ORDER BY ST_YMin(d.geom) DESC
    """)).fetchall()

print(f"{'Name':<40} {'Pts':>6} {'Parts':>5} {'Area km2':>10} {'Lat range':>15} {'Lon range':>15}")
print("-" * 100)
for r in rows:
    lat_range = f"{r[5]:.1f}-{r[6]:.1f}"
    lon_range = f"{r[7]:.1f}-{r[8]:.1f}"
    marker = " <<<" if r[5] > 65 else ""  # Arctic districts
    print(f"{r[1]:<40} {r[2]:>6} {r[3]:>5} {r[4]:>10.0f} {lat_range:>15} {lon_range:>15}{marker}")
