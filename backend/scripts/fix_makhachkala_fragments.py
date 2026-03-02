# -*- coding: utf-8 -*-
"""
Отрезать тонкие перемычки Махачкалы и передать отделившиеся куски соседним районам.
"""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

REGION = 'Республика Дагестан'
NAME = 'городской округ г. Махачкала'
BUF_NEG = -200
BUF_POS = 250

e = create_engine(settings.DATABASE_URL)

with e.begin() as c:
    rid = str(c.execute(text("SELECT id FROM regions WHERE name = :r"), {"r": REGION}).scalar())
    mid = str(c.execute(text(
        "SELECT id FROM districts WHERE region_id = :rid AND name = :n"
    ), {"rid": rid, "n": NAME}).scalar())

    # 1. Вычисляем главную часть = пересечение оригинала с расширенной главной shrunk частью
    main_geom = c.execute(text("""
        WITH orig AS (
            SELECT geom FROM districts WHERE id = :mid
        ),
        shrunk AS (
            SELECT ST_CollectionExtract(ST_MakeValid(
                ST_Buffer(geom::geography, :buf)::geometry
            ), 3) AS geom FROM orig
        ),
        main_shrunk AS (
            SELECT (dump).geom AS gp
            FROM shrunk, LATERAL ST_Dump(geom) AS dump
            ORDER BY ST_Area((dump).geom::geography) DESC
            LIMIT 1
        ),
        main_expanded AS (
            SELECT ST_MakeValid(ST_Buffer(ms.gp::geography, :buf_pos)::geometry) AS gp_exp
            FROM main_shrunk ms
        ),
        main_real AS (
            SELECT ST_Multi(ST_CollectionExtract(ST_MakeValid(
                ST_Intersection(orig.geom, me.gp_exp)
            ), 3)) AS geom
            FROM orig, main_expanded me
        )
        SELECT ST_AsEWKB(geom),
               ROUND((ST_Area(geom::geography)/1e6)::numeric, 2)
        FROM main_real
    """), {"mid": mid, "buf": BUF_NEG, "buf_pos": BUF_POS}).fetchone()

    main_wkb = main_geom[0]
    main_km2 = main_geom[1]
    print(f"Main part: {main_km2} km2")

    # 2. Осколки = оригинал - главная часть
    frag_geom = c.execute(text("""
        SELECT ST_AsEWKB(
            ST_CollectionExtract(ST_MakeValid(
                ST_Difference(d.geom, CAST(:main_geom AS geometry))
            ), 3)
        ),
        ROUND((ST_Area(ST_CollectionExtract(ST_MakeValid(
            ST_Difference(d.geom, CAST(:main_geom AS geometry))
        ), 3)::geography)/1e6)::numeric, 2),
        ST_IsEmpty(ST_CollectionExtract(ST_MakeValid(
            ST_Difference(d.geom, CAST(:main_geom AS geometry))
        ), 3))
        FROM districts d WHERE d.id = :mid
    """), {"mid": mid, "main_geom": main_wkb}).fetchone()

    frag_total_km2 = frag_geom[1]
    frag_empty = frag_geom[2]
    print(f"Fragments total: {frag_total_km2} km2, empty={frag_empty}")

    if frag_empty or frag_total_km2 == 0:
        print("No fragments to transfer")
        sys.exit(0)

    # 3. Dump каждый фрагмент
    frag_parts = c.execute(text("""
        WITH frags AS (
            SELECT ST_CollectionExtract(ST_MakeValid(
                ST_Difference(d.geom, CAST(:main_geom AS geometry))
            ), 3) AS geom
            FROM districts d WHERE d.id = :mid
        )
        SELECT ST_AsEWKB((dump).geom),
               ROUND((ST_Area((dump).geom::geography)/1e6)::numeric, 4) AS km2,
               ROUND(ST_Y(ST_Centroid((dump).geom))::numeric, 4) AS lat,
               ROUND(ST_X(ST_Centroid((dump).geom))::numeric, 4) AS lon
        FROM frags, LATERAL ST_Dump(geom) AS dump
        ORDER BY ST_Area((dump).geom::geography) DESC
    """), {"mid": mid, "main_geom": main_wkb}).fetchall()

    print(f"\nFragment pieces: {len(frag_parts)}")
    for i, fp in enumerate(frag_parts):
        print(f"  #{i+1}: {fp[1]} km2, lat={fp[2]}, lon={fp[3]}")

    # 4. Передаём каждый фрагмент подходящему району
    for i, fp in enumerate(frag_parts):
        fwkb = fp[0]
        fkm2 = fp[1]
        flat = fp[2]
        flon = fp[3]

        target = c.execute(text("""
            SELECT d.id, d.name
            FROM districts d
            WHERE d.region_id = :rid AND d.id != :mid AND d.geom IS NOT NULL
              AND ST_Contains(d.geom, ST_Centroid(CAST(:fg AS geometry)))
            LIMIT 1
        """), {"rid": rid, "mid": mid, "fg": fwkb}).fetchone()

        if not target:
            target = c.execute(text("""
                SELECT d.id, d.name
                FROM districts d
                WHERE d.region_id = :rid AND d.id != :mid AND d.geom IS NOT NULL
                  AND ST_Intersects(d.geom, CAST(:fg AS geometry))
                ORDER BY ST_Area(ST_Intersection(d.geom, CAST(:fg AS geometry))::geography) DESC
                LIMIT 1
            """), {"rid": rid, "mid": mid, "fg": fwkb}).fetchone()

        if not target:
            target = c.execute(text("""
                SELECT d.id, d.name
                FROM districts d
                WHERE d.region_id = :rid AND d.id != :mid AND d.geom IS NOT NULL
                ORDER BY ST_Distance(d.geom::geography, ST_Centroid(CAST(:fg AS geometry))::geography)
                LIMIT 1
            """), {"rid": rid, "mid": mid, "fg": fwkb}).fetchone()

        if target:
            print(f"  #{i+1} ({fkm2} km2, lat={flat}) -> {target[1]}")
            c.execute(text("""
                UPDATE districts SET geom = ST_Multi(ST_CollectionExtract(ST_MakeValid(
                    ST_Union(geom, CAST(:fg AS geometry))
                ), 3))
                WHERE id = :tid
            """), {"tid": str(target[0]), "fg": fwkb})
        else:
            print(f"  #{i+1} ({fkm2} km2) -> NO TARGET!")

    # 5. Обновляем Махачкалу = только главная часть
    c.execute(text("UPDATE districts SET geom = CAST(:mg AS geometry) WHERE id = :mid"),
              {"mid": mid, "mg": main_wkb})

    new_area = c.execute(text(
        "SELECT ROUND((ST_Area(geom::geography)/1e6)::numeric, 2) FROM districts WHERE id = :mid"
    ), {"mid": mid}).scalar()
    print(f"\nMakhachkala after fix: {new_area} km2")

    # 6. Обновляем geom_simplified для всех
    c.execute(text("""
        UPDATE districts SET geom_simplified = ST_SimplifyPreserveTopology(geom, 0.01)
        WHERE region_id = :rid AND geom IS NOT NULL
    """), {"rid": rid})

print("Done!")

# Проверка
with e.connect() as c:
    multi = c.execute(text("""
        SELECT d.name, ST_NumGeometries(d.geom)
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = :region AND d.geom IS NOT NULL AND ST_NumGeometries(d.geom) > 1
    """), {"region": REGION}).fetchall()
    if multi:
        print("Districts with >1 part:")
        for m in multi:
            print(f"  {m[0]}: {m[1]} parts")
    else:
        print("All districts have 1 part!")
