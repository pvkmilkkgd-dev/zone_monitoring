# -*- coding: utf-8 -*-
"""
Осколки перечисленных районов лежат внутри Бабаюртовского.
Присоединить эти осколки к Бабаюртовскому и убрать из геометрий этих районов.
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

    conn.execute(text("DROP TABLE IF EXISTS _babay_geom"))
    conn.execute(
        text("CREATE TEMP TABLE _babay_geom AS SELECT geom FROM districts WHERE id = :bid"),
        {"bid": babay_id},
    )

    # 1) Присоединить к Бабаюртовскому осколки этих 10 районов, лежащие внутри него
    conn.execute(
        text("""
            WITH babay AS (SELECT geom FROM _babay_geom),
            others_inside AS (
                SELECT ST_Intersection(o.geom, b.geom) AS overlap
                FROM districts o
                JOIN regions r ON o.region_id = r.id,
                babay b
                WHERE r.name = :region
                  AND o.name = ANY(:names)
                  AND o.geom IS NOT NULL
                  AND ST_Intersects(o.geom, b.geom)
            ),
            merged AS (SELECT ST_Union(overlap) AS geom FROM others_inside)
            UPDATE districts d SET geom = ST_Multi(ST_MakeValid(ST_Union(d.geom, COALESCE((SELECT geom FROM merged), ST_GeomFromText('POLYGON EMPTY', 4326)))))
            WHERE d.id = :bid
        """),
        {"bid": babay_id, "region": REGION, "names": DISTRICTS_WITH_FRAGMENTS_IN_BABAY},
    )

    # 2) У этих 10 районов вычесть область Бабаюртовского
    conn.execute(
        text("""
            WITH babay AS (SELECT geom FROM _babay_geom),
            diff AS (
                SELECT d.id, ST_Multi(ST_MakeValid(ST_Difference(d.geom, b.geom))) AS new_geom
                FROM districts d
                JOIN regions r ON d.region_id = r.id,
                babay b
                WHERE r.name = :region
                  AND d.name = ANY(:names)
                  AND d.geom IS NOT NULL
                  AND ST_Intersects(d.geom, b.geom)
            )
            UPDATE districts d SET geom = CASE
                WHEN diff.new_geom IS NULL OR ST_IsEmpty(diff.new_geom) THEN d.geom
                ELSE diff.new_geom
            END
            FROM diff
            WHERE d.id = diff.id
        """),
        {"region": REGION, "names": DISTRICTS_WITH_FRAGMENTS_IN_BABAY},
    )

    conn.execute(text("DROP TABLE IF EXISTS _babay_geom"))

print("OK: осколки 10 районов внутри Бабаюртовского присоединены к Бабаюртовскому и убраны у этих районов.")
