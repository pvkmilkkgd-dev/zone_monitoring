# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    # Region geometry
    r = c.execute(text("""
        SELECT name,
               ROUND(ST_XMin(geom)::numeric, 2), ROUND(ST_XMax(geom)::numeric, 2),
               ROUND(ST_XMin(geom_simplified)::numeric, 2), ROUND(ST_XMax(geom_simplified)::numeric, 2),
               ROUND((ST_Area(geom::geography)/1e6)::numeric, 0)
        FROM regions WHERE name ILIKE '%Чукот%'
    """)).fetchone()
    if r:
        print(f"Region '{r[0]}':")
        print(f"  geom:            lon {r[1]} .. {r[2]}")
        print(f"  geom_simplified: lon {r[3]} .. {r[4]}")
        print(f"  area: {r[5]} km2")
    
    # District geom vs geom_simplified
    print("\nDistricts:")
    rows = c.execute(text("""
        SELECT d.name,
               ROUND(ST_XMin(d.geom)::numeric, 2), ROUND(ST_XMax(d.geom)::numeric, 2),
               ROUND(ST_XMin(d.geom_simplified)::numeric, 2), ROUND(ST_XMax(d.geom_simplified)::numeric, 2)
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name ILIKE '%Чукот%' AND d.geom IS NOT NULL
        ORDER BY d.name
    """)).fetchall()
    for r in rows:
        gs_ok = "OK" if r[3] > 0 else "!!!"
        print(f"  {r[0]:<45s}  geom: {r[1]:>8.2f}..{r[2]:>8.2f}  simpl: {r[3]:>8.2f}..{r[4]:>8.2f}  {gs_ok}")

    # Check what ST_AsGeoJSON returns for the shifted coordinates
    print("\nST_AsGeoJSON bbox check (Чукотский):")
    gj = c.execute(text("""
        SELECT substring(ST_AsGeoJSON(d.geom)::text, 1, 200)
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name ILIKE '%Чукот%' AND d.name = 'Чукотский муниципальный район'
    """)).scalar()
    if gj:
        print(f"  {gj}")
