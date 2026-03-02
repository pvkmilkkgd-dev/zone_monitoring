# -*- coding: utf-8 -*-
"""Вернуть координаты Чукотки обратно в -180..180 (ST_ShiftLongitude — toggle)."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)

with e.begin() as c:
    # Districts
    c.execute(text("""
        UPDATE districts
        SET geom = ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_ShiftLongitude(geom)), 3))
        WHERE region_id = (SELECT id FROM regions WHERE name = 'Чукотский автономный округ')
          AND geom IS NOT NULL
    """))
    c.execute(text("""
        UPDATE districts
        SET geom_simplified = ST_SimplifyPreserveTopology(geom, 0.01)
        WHERE region_id = (SELECT id FROM regions WHERE name = 'Чукотский автономный округ')
          AND geom IS NOT NULL
    """))

    # Region
    c.execute(text("""
        UPDATE regions
        SET geom = ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_ShiftLongitude(geom)), 3))
        WHERE name = 'Чукотский автономный округ' AND geom IS NOT NULL
    """))
    c.execute(text("""
        UPDATE regions
        SET geom_simplified = ST_SimplifyPreserveTopology(geom, 0.01)
        WHERE name = 'Чукотский автономный округ' AND geom IS NOT NULL
    """))

    # Check
    rows = c.execute(text("""
        SELECT d.name,
               ROUND(ST_XMin(d.geom)::numeric, 2), ROUND(ST_XMax(d.geom)::numeric, 2)
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Чукотский автономный округ' AND d.geom IS NOT NULL
        ORDER BY d.name
    """)).fetchall()
    print("Districts:")
    for r in rows:
        print(f"  {r[0]:<45s}  lon: {r[1]:>8.2f} .. {r[2]:>8.2f}")

    rr = c.execute(text("""
        SELECT ROUND(ST_XMin(geom)::numeric, 2), ROUND(ST_XMax(geom)::numeric, 2)
        FROM regions WHERE name = 'Чукотский автономный округ'
    """)).fetchone()
    print(f"\nRegion: lon {rr[0]} .. {rr[1]}")

print("Done!")
