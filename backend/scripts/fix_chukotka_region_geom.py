# -*- coding: utf-8 -*-
"""Исправить антимеридиан для геометрии региона Чукотка (таблица regions)."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)

with e.begin() as c:
    # Геометрия региона
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

    r = c.execute(text("""
        SELECT ROUND(ST_XMin(geom)::numeric, 2), ROUND(ST_XMax(geom)::numeric, 2),
               ROUND(ST_XMin(geom_simplified)::numeric, 2), ROUND(ST_XMax(geom_simplified)::numeric, 2)
        FROM regions WHERE name = 'Чукотский автономный округ'
    """)).fetchone()
    print(f"Region geom:       lon {r[0]} .. {r[1]}")
    print(f"Region simplified: lon {r[2]} .. {r[3]}")

print("Done!")
