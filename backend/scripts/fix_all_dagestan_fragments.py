# -*- coding: utf-8 -*-
"""
Убрать ВСЕ осколки у всех районов Дагестана.
Для каждого района: оставляем только главную часть (самую большую),
остальные передаём в район, на территории которого они находятся.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
REGION = "Республика Дагестан"


def main():
    with engine.begin() as conn:
        rid = conn.execute(text("SELECT id FROM regions WHERE name = :r"), {"r": REGION}).scalar()
        if not rid:
            print("Region not found")
            return
        rid = str(rid)

        # Backup
        conn.execute(text("DROP TABLE IF EXISTS _dag_all_backup"))
        conn.execute(text("""
            CREATE TEMP TABLE _dag_all_backup AS
            SELECT id, name, geom FROM districts WHERE region_id = :rid AND geom IS NOT NULL
        """), {"rid": rid})

        # Все осколки (rn > 1 = не главная часть)
        conn.execute(text("DROP TABLE IF EXISTS _dag_fragments"))
        conn.execute(text("""
            CREATE TEMP TABLE _dag_fragments AS
            WITH ranked AS (
                SELECT d.id as source_id, d.name as source_name,
                       (dump).geom as piece_geom,
                       ROUND((ST_Area((dump).geom::geography)/1000000)::numeric, 2) as piece_km2,
                       ROW_NUMBER() OVER (PARTITION BY d.id ORDER BY ST_Area((dump).geom::geography) DESC) as rn
                FROM districts d
                JOIN regions r ON d.region_id = r.id,
                LATERAL ST_Dump(d.geom) AS dump
                WHERE r.name = :region AND ST_NumGeometries(d.geom) > 1
            )
            SELECT source_id, source_name, piece_geom, piece_km2
            FROM ranked WHERE rn > 1
        """), {"region": REGION})

        n = conn.execute(text("SELECT count(*) FROM _dag_fragments")).scalar()
        if n == 0:
            print("Oskolkov net")
            conn.execute(text("DROP TABLE IF EXISTS _dag_all_backup"))
            return
        print(f"Oskolkov: {n}")

        # target: centroid -> intersects -> nearest
        conn.execute(text("ALTER TABLE _dag_fragments ADD COLUMN target_id uuid"))
        conn.execute(text("""
            UPDATE _dag_fragments f SET target_id = (
                SELECT b.id FROM _dag_all_backup b
                WHERE b.id != f.source_id
                  AND ST_Contains(b.geom, ST_Centroid(f.piece_geom))
                ORDER BY ST_Area(b.geom::geography) ASC
                LIMIT 1
            )
        """))
        conn.execute(text("""
            UPDATE _dag_fragments f SET target_id = (
                SELECT b.id FROM _dag_all_backup b
                WHERE b.id != f.source_id AND f.target_id IS NULL
                  AND ST_Intersects(b.geom, f.piece_geom)
                ORDER BY ST_Area(ST_Intersection(b.geom, f.piece_geom)::geography) DESC
                LIMIT 1
            )
            WHERE f.target_id IS NULL
        """))
        conn.execute(text("""
            UPDATE _dag_fragments f SET target_id = (
                SELECT b.id FROM _dag_all_backup b
                WHERE b.id != f.source_id AND f.target_id IS NULL
                ORDER BY ST_Distance(b.geom::geography, f.piece_geom::geography)
                LIMIT 1
            )
            WHERE f.target_id IS NULL
        """))

        rows = conn.execute(text("""
            SELECT f.source_name, b.name as target_name, f.piece_km2
            FROM _dag_fragments f
            JOIN _dag_all_backup b ON b.id = f.target_id
            WHERE f.target_id IS NOT NULL
            ORDER BY f.source_name, f.piece_km2 DESC
        """)).fetchall()
        for row in rows:
            print(f"  {row[0]} -> {row[1]}: {row[2]} km2")

        # Add to targets
        conn.execute(text("""
            WITH to_add AS (
                SELECT target_id, ST_Union(piece_geom) AS geom
                FROM _dag_fragments WHERE target_id IS NOT NULL
                GROUP BY target_id
            )
            UPDATE districts d SET geom = ST_Multi(ST_MakeValid(ST_Union(d.geom, a.geom)))
            FROM to_add a WHERE d.id = a.target_id
        """))

        # Remove from sources: keep only main part
        conn.execute(text("""
            WITH main_only AS (
                SELECT d.id, ST_Multi((dump).geom) AS geom
                FROM districts d JOIN regions r ON d.region_id = r.id,
                LATERAL ST_Dump(d.geom) AS dump
                WHERE r.name = :region AND ST_NumGeometries(d.geom) > 1
                ORDER BY d.id, ST_Area((dump).geom::geography) DESC
            ),
            first_part AS (
                SELECT DISTINCT ON (id) id, geom FROM main_only
            )
            UPDATE districts d SET geom = f.geom
            FROM first_part f WHERE d.id = f.id
        """), {"region": REGION})

        conn.execute(text("DROP TABLE IF EXISTS _dag_all_backup"))
        conn.execute(text("DROP TABLE IF EXISTS _dag_fragments"))

        # Update simplified
        conn.execute(text("""
            UPDATE districts d SET geom_simplified = ST_SimplifyPreserveTopology(d.geom, 0.005)
            FROM regions r
            WHERE d.region_id = r.id AND r.name = :region AND d.geom IS NOT NULL
        """), {"region": REGION})

    # Verify
    print("\nProverka:")
    with engine.connect() as c:
        remaining = c.execute(text("""
            SELECT d.name, ST_NumGeometries(d.geom) as parts
            FROM districts d JOIN regions r ON d.region_id = r.id
            WHERE r.name = :region AND d.geom IS NOT NULL AND ST_NumGeometries(d.geom) > 1
            ORDER BY d.name
        """), {"region": REGION}).fetchall()
        if remaining:
            for r in remaining:
                print(f"  {r[0]}: {r[1]} parts")
        else:
            print("  Vse rayony - po 1 chasti!")


if __name__ == "__main__":
    main()
