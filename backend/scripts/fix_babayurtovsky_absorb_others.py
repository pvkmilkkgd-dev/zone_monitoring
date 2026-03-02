# -*- coding: utf-8 -*-
"""
Из Бабаюртовского муниципального района «удалить» осколки и дыры всех других районов:
т.е. участки других районов, лежащие внутри Бабаюртовского, присоединить к Бабаюртовскому
и убрать из геометрий этих других районов.
"""
from sqlalchemy import create_engine, text

engine = create_engine("postgresql+psycopg://zone_user:zone_password@localhost:5432/zone_monitoring")
REGION = "Республика Дагестан"
BABAY_NAME = "Бабаюртовский муниципальный район"

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

    # Сохраняем исходную геометрию Бабаюртовского для вычитания у других
    conn.execute(text("DROP TABLE IF EXISTS _babay_geom"))
    conn.execute(
        text("CREATE TEMP TABLE _babay_geom AS SELECT geom FROM districts WHERE id = :bid"),
        {"bid": babay_id},
    )

    # 1) Присоединить к Бабаюртовскому всё, что другие районы имеют внутри его границ
    conn.execute(
        text("""
            WITH babay AS (SELECT geom FROM _babay_geom),
            others_inside AS (
                SELECT ST_Intersection(o.geom, b.geom) AS overlap
                FROM districts o, babay b
                WHERE o.region_id = (SELECT region_id FROM districts WHERE id = :bid)
                  AND o.id != :bid
                  AND o.geom IS NOT NULL
                  AND ST_Intersects(o.geom, b.geom)
            ),
            merged AS (
                SELECT ST_Union(overlap) AS geom FROM others_inside
            )
            UPDATE districts d SET geom = ST_Multi(ST_MakeValid(ST_Union(d.geom, COALESCE((SELECT geom FROM merged), ST_GeomFromText('POLYGON EMPTY', 4326)))))
            WHERE d.id = :bid
        """),
        {"bid": babay_id},
    )

    # 2) У остальных районов Дагестана вычесть область Бабаюртовского (по исходной границе)
    conn.execute(
        text("""
            WITH babay AS (SELECT geom FROM _babay_geom),
            diff AS (
                SELECT d.id, ST_Multi(ST_MakeValid(ST_Difference(d.geom, b.geom))) AS new_geom
                FROM districts d, babay b
                WHERE d.region_id = (SELECT region_id FROM districts WHERE id = :bid)
                  AND d.id != :bid
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
        {"bid": babay_id},
    )

    conn.execute(text("DROP TABLE IF EXISTS _babay_geom"))

print("OK: осколки и дыры других районов внутри Бабаюртовского присоединены к Бабаюртовскому и убраны у остальных.")
