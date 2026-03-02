# -*- coding: utf-8 -*-
"""
Тарумовский муниципальный район:
1. Заполнить дыру (если есть)
2. Убрать осколки и передать их территориям, где они находятся (в т.ч. Кизлярскому)
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
REGION = "Республика Дагестан"
NAME = "Тарумовский муниципальный район"

def main():
    with engine.begin() as conn:
        rid = conn.execute(text("SELECT id FROM regions WHERE name = :r"), {"r": REGION}).scalar()
        if not rid:
            print("Регион не найден")
            return
        rid = str(rid)

        # Backup для поиска целевых районов
        conn.execute(text("DROP TABLE IF EXISTS _dag_backup"))
        conn.execute(text("""
            CREATE TEMP TABLE _dag_backup AS
            SELECT id, name, geom FROM districts WHERE region_id = :rid AND geom IS NOT NULL
        """), {"rid": rid})

        # 1. Дыры — передать в ближайший район (Intersects или min Distance)
        conn.execute(text("""
            WITH holes AS (
                SELECT d.id as src_id,
                       ST_SetSRID(ST_MakePolygon(ST_InteriorRingN((dump).geom, i)), 4326) AS hole_geom
                FROM districts d JOIN regions r ON d.region_id = r.id,
                LATERAL ST_Dump(d.geom) AS dump,
                LATERAL generate_series(1, ST_NumInteriorRings((dump).geom)) AS i
                WHERE r.name = :region AND d.name = :name
            ),
            best_target AS (
                SELECT DISTINCT ON (h.src_id, (h.hole_geom)::text) h.hole_geom,
                    COALESCE(
                        (SELECT b.id FROM _dag_backup b
                         WHERE b.id != h.src_id AND ST_Intersects(b.geom, h.hole_geom)
                         ORDER BY ST_Area(ST_Intersection(b.geom, h.hole_geom)::geography) DESC
                         LIMIT 1),
                        (SELECT b.id FROM _dag_backup b
                         WHERE b.id != h.src_id
                         ORDER BY ST_Distance(b.geom::geography, h.hole_geom::geography)
                         LIMIT 1)
                    ) as target_id
                FROM holes h
            ),
            by_target AS (
                SELECT target_id, ST_Union(hole_geom) as geom
                FROM best_target WHERE target_id IS NOT NULL GROUP BY target_id
            )
            UPDATE districts d SET geom = ST_Multi(ST_MakeValid(ST_Union(d.geom, b.geom)))
            FROM by_target b WHERE d.id = b.target_id
        """), {"region": REGION, "name": NAME})

        # Убрать дыры из Тарумовского (оставить только внешние кольца)
        conn.execute(text("""
            UPDATE districts d SET geom = sub.geom
            FROM (
                SELECT d.id,
                       ST_Multi(ST_Union(ST_MakePolygon(ST_ExteriorRing((dump).geom)))) AS geom
                FROM districts d JOIN regions r ON d.region_id = r.id,
                LATERAL ST_Dump(d.geom) AS dump
                WHERE r.name = :region AND d.name = :name
                GROUP BY d.id
            ) sub
            WHERE d.id = sub.id
        """), {"region": REGION, "name": NAME})

        # 2. Осколки — передать в содержащие районы
        conn.execute(text("DROP TABLE IF EXISTS _dag_backup"))
        conn.execute(text("""
            CREATE TEMP TABLE _dag_backup AS
            SELECT id, name, geom FROM districts WHERE region_id = :rid AND geom IS NOT NULL
        """), {"rid": rid})

        conn.execute(text("DROP TABLE IF EXISTS _tarum_fragments"))
        conn.execute(text("""
            CREATE TEMP TABLE _tarum_fragments AS
            WITH ranked AS (
                SELECT d.id as source_id, d.name as source_name,
                       (dump).geom as piece_geom,
                       ROUND((ST_Area((dump).geom::geography)/1000000)::numeric, 1) as piece_km2,
                       ROW_NUMBER() OVER (PARTITION BY d.id ORDER BY ST_Area((dump).geom::geography) DESC) as rn
                FROM districts d
                JOIN regions r ON d.region_id = r.id,
                LATERAL ST_Dump(d.geom) AS dump
                WHERE r.name = :region AND d.name = :name
            )
            SELECT source_id, source_name, piece_geom, piece_km2
            FROM ranked WHERE rn > 1
        """), {"region": REGION, "name": NAME})

        n = conn.execute(text("SELECT count(*) FROM _tarum_fragments")).scalar()
        if n == 0:
            print("Осколков нет.")
            conn.execute(text("DROP TABLE IF EXISTS _dag_backup"))
            conn.execute(text("DROP TABLE IF EXISTS _tarum_fragments"))
        else:
            conn.execute(text("ALTER TABLE _tarum_fragments ADD COLUMN target_id uuid"))
            conn.execute(text("""
                UPDATE _tarum_fragments f SET target_id = (
                    SELECT b.id FROM _dag_backup b
                    WHERE b.id != f.source_id AND ST_Contains(b.geom, ST_Centroid(f.piece_geom))
                    ORDER BY ST_Area(b.geom::geography) ASC LIMIT 1
                )
            """))
            conn.execute(text("""
                UPDATE _tarum_fragments f SET target_id = (
                    SELECT b.id FROM _dag_backup b
                    WHERE b.id != f.source_id AND f.target_id IS NULL AND ST_Intersects(b.geom, f.piece_geom)
                    ORDER BY ST_Area(ST_Intersection(b.geom, f.piece_geom)::geography) DESC LIMIT 1
                )
                WHERE f.target_id IS NULL
            """))

            rows = conn.execute(text("""
                SELECT f.source_name, b.name, f.piece_km2
                FROM _tarum_fragments f JOIN _dag_backup b ON b.id = f.target_id
                WHERE f.target_id IS NOT NULL
            """)).fetchall()
            for row in rows:
                print(f"  {row[0]} -> {row[1]}: {row[2]} km2")

            conn.execute(text("""
                WITH to_add AS (
                    SELECT target_id, ST_Union(piece_geom) AS geom
                    FROM _tarum_fragments WHERE target_id IS NOT NULL GROUP BY target_id
                )
                UPDATE districts d SET geom = ST_Multi(ST_MakeValid(ST_Union(d.geom, a.geom)))
                FROM to_add a WHERE d.id = a.target_id
            """))

            conn.execute(text("""
                WITH main AS (
                    SELECT d.id, ST_Multi((dump).geom) AS geom
                    FROM districts d JOIN regions r ON d.region_id = r.id,
                    LATERAL ST_Dump(d.geom) AS dump
                    WHERE r.name = :region AND d.name = :name
                    ORDER BY d.id, ST_Area((dump).geom::geography) DESC
                ),
                first AS (SELECT DISTINCT ON (id) id, geom FROM main)
                UPDATE districts d SET geom = f.geom FROM first f WHERE d.id = f.id
            """), {"region": REGION, "name": NAME})

            conn.execute(text("DROP TABLE IF EXISTS _dag_backup"))
            conn.execute(text("DROP TABLE IF EXISTS _tarum_fragments"))

        conn.execute(text("""
            UPDATE districts d SET geom_simplified = ST_SimplifyPreserveTopology(d.geom, 0.005)
            FROM regions r WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
        """), {"region": REGION, "name": NAME})

    r = engine.connect().execute(text("""
        SELECT ST_NumGeometries(d.geom), ROUND((ST_Area(d.geom::geography)/1000000)::numeric, 1)
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = :region AND d.name = :name
    """), {"region": REGION, "name": NAME}).fetchone()
    print(f"Готово: {r[0]} частей, {r[1]} km2")

if __name__ == "__main__":
    main()
