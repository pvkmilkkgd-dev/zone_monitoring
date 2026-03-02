# -*- coding: utf-8 -*-
"""
Осколки перечисленных районов (целиком лежащие внутри Бабаюртовского) присоединить
к Бабаюртовскому и убрать из этих районов. Используем ST_Within(part, babay) по частям полигонов.
"""
from sqlalchemy import create_engine, text

engine = create_engine("postgresql+psycopg://zone_user:zone_password@localhost:5432/zone_monitoring")
REGION = "Республика Дагестан"
BABAY_NAME = "Бабаюртовский муниципальный район"

DISTRICTS_WITH_FRAGMENTS_IN_BABAY = [
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

with engine.begin() as conn:
    babay_id = conn.execute(
        text("""
            SELECT d.id FROM districts d
            JOIN regions r ON d.region_id = r.id
            WHERE r.name = :region AND d.name = :name
        """),
        {"region": REGION, "name": BABAY_NAME},
    ).scalar()
    if not babay_id:
        print("Бабаюртовский район не найден.")
        exit(1)

    # Область Бабаюртовского: контур без дыр (внешние кольца), чтобы осколки в «дырах» тоже учитывались
    conn.execute(text("DROP TABLE IF EXISTS _babay_geom"))
    conn.execute(
        text("""
            CREATE TEMP TABLE _babay_geom AS
            SELECT ST_Union(ST_MakePolygon(ST_ExteriorRing((dump).geom))) AS g
            FROM districts, LATERAL ST_Dump(geom) AS dump WHERE id = :bid
        """),
        {"bid": babay_id},
    )

    # 1) Собрать все части перечисленных районов, которые целиком внутри области Бабаюртовского (контур без дыр)
    conn.execute(text("DROP TABLE IF EXISTS _parts_inside_babay"))
    conn.execute(
        text("""
            CREATE TEMP TABLE _parts_inside_babay (part_geom geometry)
        """)
    )
    conn.execute(
        text("""
            INSERT INTO _parts_inside_babay (part_geom)
            SELECT (dump).geom
            FROM districts o
            JOIN regions r ON o.region_id = r.id,
            (SELECT g FROM _babay_geom) b,
            LATERAL ST_Dump(o.geom) AS dump
            WHERE r.name = :region
              AND o.name = ANY(:names)
              AND o.geom IS NOT NULL
              AND ST_Within((dump).geom, b.g)
        """),
        {"region": REGION, "names": DISTRICTS_WITH_FRAGMENTS_IN_BABAY},
    )
    n_parts = conn.execute(text("SELECT count(*) FROM _parts_inside_babay")).scalar()
    if n_parts > 0:
        # Присоединить эти части к Бабаюртовскому
        conn.execute(
            text("""
                UPDATE districts d SET geom = ST_Multi(ST_MakeValid(ST_Union(d.geom, p.merged)))
                FROM (SELECT ST_Union(part_geom) AS merged FROM _parts_inside_babay) p
                WHERE d.id = :bid
            """),
            {"bid": babay_id},
        )

    # 2) У каждого из 10 районов оставить только части, НЕ лежащие целиком внутри Бабаюртовского
    conn.execute(
        text("""
            WITH babay AS (SELECT g FROM _babay_geom),
            filtered AS (
                SELECT o.id, (dump).geom AS part
                FROM districts o
                JOIN regions r ON o.region_id = r.id,
                babay b,
                LATERAL ST_Dump(o.geom) AS dump
                WHERE r.name = :region
                  AND o.name = ANY(:names)
                  AND o.geom IS NOT NULL
                  AND NOT ST_Within((dump).geom, b.g)
            ),
            new_geoms AS (
                SELECT id, ST_Multi(ST_Union(part)) AS geom FROM filtered GROUP BY id
            )
            UPDATE districts d SET geom = CASE
                WHEN ng.geom IS NULL OR ST_IsEmpty(ng.geom) THEN d.geom
                ELSE ng.geom
            END
            FROM new_geoms ng
            WHERE d.id = ng.id
        """),
        {"region": REGION, "names": DISTRICTS_WITH_FRAGMENTS_IN_BABAY},
    )

    conn.execute(text("DROP TABLE IF EXISTS _parts_inside_babay"))
    conn.execute(text("DROP TABLE IF EXISTS _babay_geom"))

    print(f"OK: найдено частей внутри Бабаюртовского: {n_parts}. Осколки присоединены к Бабаюртовскому и убраны у 10 районов.")
