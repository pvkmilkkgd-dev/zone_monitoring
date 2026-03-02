# -*- coding: utf-8 -*-
"""
Отрезать северный «хвост» Махачкалы и передать его Буйнакскому району.
Используем отрицательный буфер чтобы отделить хвост от основного тела,
затем передаём все части кроме главной Буйнакскому.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
REGION = "Республика Дагестан"
SRC = "городской округ г. Махачкала"
TGT = "Буйнакский муниципальный район"

with engine.connect() as conn:
    before = conn.execute(text("""
        SELECT ST_NPoints(d.geom), ST_NumGeometries(d.geom),
               ROUND((ST_Area(d.geom::geography)/1000000)::numeric, 1)
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = :region AND d.name = :src
    """), {"region": REGION, "src": SRC}).fetchone()
    print(f"Before: {before[0]} pts, {before[1]} parts, {before[2]} km2")

with engine.begin() as conn:
    # Отрицательный буфер разрывает тонкую связь хвоста с основным телом
    for buf_m in [100, 200, 500, 1000]:
        n_parts = conn.execute(text("""
            SELECT ST_NumGeometries(ST_CollectionExtract(ST_MakeValid(
                ST_Buffer(ST_Buffer(d.geom::geography, :buf_neg)::geometry, 0)
            ), 3))
            FROM districts d JOIN regions r ON d.region_id = r.id
            WHERE r.name = :region AND d.name = :src
        """), {"region": REGION, "src": SRC, "buf_neg": -buf_m}).scalar()
        print(f"  buffer -{buf_m}m: {n_parts} parts")
        if n_parts and n_parts > 1:
            # Нашли буфер, который разделяет. Используем его.
            # Отрицательный буфер -> dump -> положительный буфер обратно -> главная часть остаётся
            conn.execute(text("""
                WITH orig AS (
                    SELECT d.id, d.geom FROM districts d JOIN regions r ON d.region_id = r.id
                    WHERE r.name = :region AND d.name = :src
                ),
                shrunk AS (
                    SELECT id, ST_CollectionExtract(ST_MakeValid(
                        ST_Buffer(geom::geography, :buf_neg)::geometry
                    ), 3) AS geom FROM orig
                ),
                parts AS (
                    SELECT id, (dump).geom AS part_geom,
                           ST_Area((dump).geom::geography) AS area,
                           ROW_NUMBER() OVER (ORDER BY ST_Area((dump).geom::geography) DESC) AS rn
                    FROM shrunk, LATERAL ST_Dump(geom) AS dump
                ),
                main_shrunk AS (
                    SELECT part_geom FROM parts WHERE rn = 1
                ),
                -- Главная часть Махачкалы = пересечение оригинала с буфером обратно главной shrunk части
                main_expanded AS (
                    SELECT ST_Multi(ST_MakeValid(ST_Intersection(
                        orig.geom,
                        ST_Buffer(ms.part_geom::geography, :buf_pos)::geometry
                    ))) AS geom
                    FROM orig, main_shrunk ms
                ),
                -- Хвост = разница оригинала и главной расширенной части
                tail AS (
                    SELECT ST_CollectionExtract(
                        ST_Difference(orig.geom, me.geom), 3
                    ) AS geom
                    FROM orig, main_expanded me
                )
                SELECT ROUND((ST_Area(me.geom::geography)/1000000)::numeric, 1) as main_km2,
                       ROUND((ST_Area(t.geom::geography)/1000000)::numeric, 1) as tail_km2
                FROM main_expanded me, tail t
            """), {"region": REGION, "src": SRC, "buf_neg": -buf_m, "buf_pos": buf_m + 50}).fetchone()

            # Применяем
            conn.execute(text("""
                WITH orig AS (
                    SELECT d.id, d.geom FROM districts d JOIN regions r ON d.region_id = r.id
                    WHERE r.name = :region AND d.name = :src
                ),
                shrunk AS (
                    SELECT id, ST_CollectionExtract(ST_MakeValid(
                        ST_Buffer(geom::geography, :buf_neg)::geometry
                    ), 3) AS geom FROM orig
                ),
                parts AS (
                    SELECT (dump).geom AS part_geom,
                           ROW_NUMBER() OVER (ORDER BY ST_Area((dump).geom::geography) DESC) AS rn
                    FROM shrunk, LATERAL ST_Dump(geom) AS dump
                ),
                main_shrunk AS (SELECT part_geom FROM parts WHERE rn = 1),
                main_expanded AS (
                    SELECT ST_Multi(ST_MakeValid(ST_Intersection(
                        orig.geom,
                        ST_Buffer(ms.part_geom::geography, :buf_pos)::geometry
                    ))) AS geom
                    FROM orig, main_shrunk ms
                ),
                tail AS (
                    SELECT ST_CollectionExtract(ST_Difference(orig.geom, me.geom), 3) AS geom
                    FROM orig, main_expanded me
                )
                -- Передать хвост Буйнакскому
                UPDATE districts d SET geom = ST_Multi(ST_MakeValid(ST_Union(d.geom, t.geom)))
                FROM tail t, regions r
                WHERE d.region_id = r.id AND r.name = :region AND d.name = :tgt
                  AND NOT ST_IsEmpty(t.geom)
            """), {"region": REGION, "src": SRC, "tgt": TGT, "buf_neg": -buf_m, "buf_pos": buf_m + 50})

            # Оставить только основную часть у Махачкалы
            conn.execute(text("""
                WITH orig AS (
                    SELECT d.id, d.geom FROM districts d JOIN regions r ON d.region_id = r.id
                    WHERE r.name = :region AND d.name = :src
                ),
                shrunk AS (
                    SELECT id, ST_CollectionExtract(ST_MakeValid(
                        ST_Buffer(geom::geography, :buf_neg)::geometry
                    ), 3) AS geom FROM orig
                ),
                parts AS (
                    SELECT (dump).geom AS part_geom,
                           ROW_NUMBER() OVER (ORDER BY ST_Area((dump).geom::geography) DESC) AS rn
                    FROM shrunk, LATERAL ST_Dump(geom) AS dump
                ),
                main_shrunk AS (SELECT part_geom FROM parts WHERE rn = 1),
                main_part AS (
                    SELECT orig.id, ST_Multi(ST_MakeValid(ST_Intersection(
                        orig.geom,
                        ST_Buffer(ms.part_geom::geography, :buf_pos)::geometry
                    ))) AS geom
                    FROM orig, main_shrunk ms
                )
                UPDATE districts d SET geom = mp.geom
                FROM main_part mp WHERE d.id = mp.id
            """), {"region": REGION, "src": SRC, "buf_neg": -buf_m, "buf_pos": buf_m + 50})

            # Update simplified
            for name in [SRC, TGT]:
                conn.execute(text("""
                    UPDATE districts d SET geom_simplified = ST_SimplifyPreserveTopology(d.geom, 0.005)
                    FROM regions r WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
                """), {"region": REGION, "name": name})

            break

with engine.connect() as conn:
    for name in [SRC, TGT]:
        r = conn.execute(text("""
            SELECT ST_NumGeometries(d.geom), ROUND((ST_Area(d.geom::geography)/1000000)::numeric, 1)
            FROM districts d JOIN regions r ON d.region_id = r.id
            WHERE r.name = :region AND d.name = :name
        """), {"region": REGION, "name": name}).fetchone()
        print(f"  {name}: {r[0]} parts, {r[1]} km2")
print("OK")
