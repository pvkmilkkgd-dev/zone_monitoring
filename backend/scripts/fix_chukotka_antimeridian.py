# -*- coding: utf-8 -*-
"""
Исправить пересечение антимеридиана (180°) у Чукотки.
ST_ShiftLongitude: переводит координаты из [-180, 0] → [180, 360],
чтобы все районы были в непрерывном диапазоне ~157..192°.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

REGION = 'Чукотский автономный округ'
engine = create_engine(settings.DATABASE_URL)

with engine.begin() as conn:
    rid = str(conn.execute(text("SELECT id FROM regions WHERE name = :r"), {"r": REGION}).scalar())

    # Применяем ST_ShiftLongitude ко всем районам Чукотки
    conn.execute(text("""
        UPDATE districts
        SET geom = ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_ShiftLongitude(geom)), 3))
        WHERE region_id = :rid AND geom IS NOT NULL
    """), {"rid": rid})

    conn.execute(text("""
        UPDATE districts
        SET geom_simplified = ST_SimplifyPreserveTopology(geom, 0.01)
        WHERE region_id = :rid AND geom IS NOT NULL
    """), {"rid": rid})

    # Проверка
    rows = conn.execute(text("""
        SELECT d.name,
               ROUND(ST_XMin(d.geom)::numeric, 2) AS lon_min,
               ROUND(ST_XMax(d.geom)::numeric, 2) AS lon_max,
               ROUND((ST_Area(d.geom::geography)/1e6)::numeric, 1) AS area
        FROM districts d WHERE d.region_id = :rid AND d.geom IS NOT NULL
        ORDER BY d.name
    """), {"rid": rid}).fetchall()

    print("После ST_ShiftLongitude:")
    for r in rows:
        ok = "OK" if r[1] > 0 else "!!!"
        print(f"  {r[0]:<45s}  lon: {r[1]:>8.2f} .. {r[2]:>8.2f}  area: {r[3]:>10.1f} km2  {ok}")

print("Done!")
