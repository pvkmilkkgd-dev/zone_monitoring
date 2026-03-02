# -*- coding: utf-8 -*-
"""Проверка: какие районы пересекаются с Бабаюртовским и есть ли части внутри него."""
from sqlalchemy import create_engine, text

engine = create_engine("postgresql+psycopg://zone_user:zone_password@localhost:5432/zone_monitoring")
REGION = "Республика Дагестан"
BABAY = "Бабаюртовский муниципальный район"

TARGET_NAMES = [
    "Цунтинский муниципальный район",
    "Гумбетовский муниципальный район",
    "Тляратинский муниципальный район",
    "Чародинский муниципальный район",
    "Рутульский муниципальный район",
    "Казбековский муниципальный район",
    "Ахвахский муниципальный район",
    "Лакский муниципальный район",
    "Цумадинский муниципальный район",
    "Ботлихский муниципальный район",
]

with engine.connect() as conn:
    # Все районы Дагестана и их имена
    all_d = conn.execute(text("""
        SELECT d.name FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name = :r ORDER BY d.name
    """), {"r": REGION}).fetchall()
    print("Районы в БД (первые 20):", [x[0] for x in all_d[:20]])
    for n in TARGET_NAMES:
        if not any(x[0] == n for x in all_d):
            print("НЕТ В БД:", repr(n))

    # Бабаюртовский geom
    row = conn.execute(text("""
        SELECT d.id, d.name, ST_AsText(ST_Centroid(d.geom)) as center
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = :r AND d.name = :n
    """), {"r": REGION, "n": BABAY}).fetchone()
    if not row:
        print("Бабаюртовский не найден по имени:", repr(BABAY))
    else:
        print("Бабаюртовский id:", row[0], "center:", row[2])

    # Все пересечения с Бабаюртовским одним запросом
    rows = conn.execute(text("""
        WITH babay AS (
            SELECT d.geom AS g FROM districts d
            JOIN regions r ON d.region_id = r.id
            WHERE r.name = :region AND d.name = :babay
        )
        SELECT o.name,
               ST_Intersects(o.geom, b.g) AS intersects,
               ROUND((ST_Area(ST_Intersection(o.geom, b.g)::geography)/1000000)::numeric, 4) AS area_km2
        FROM districts o
        JOIN regions r ON o.region_id = r.id, babay b
        WHERE r.name = :region AND o.name = ANY(:names)
    """), {"region": REGION, "babay": BABAY, "names": TARGET_NAMES}).fetchall()
    for r in rows:
        print(f"  {r[0]}: intersects={r[1]}, area_km2={r[2]}")
    if not rows:
        print("  No matching districts or no intersections.")
