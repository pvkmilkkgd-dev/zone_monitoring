# -*- coding: utf-8 -*-
"""
Передать мелкие осколки 4 районов Дагестана тем районам, на территории которых они находятся.
(центроид осколка внутри другого района -> добавить к тому району, убрать из источника)

Районы:
- Ахвахский муниципальный район
- Гумбетовский муниципальный район
- Казбековский муниципальный район
- Хасавюртовский муниципальный район
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
REGION = "Республика Дагестан"
DISTRICTS = [
    "Ахвахский муниципальный район",
    "Гумбетовский муниципальный район",
    "Казбековский муниципальный район",
    "Хасавюртовский муниципальный район",
    "городской округ г. Кизляр",
    "Кизлярский муниципальный район",
    "Ботлихский муниципальный район",
    "Сергокалинский муниципальный район",
]


def main():
    with engine.begin() as conn:
        rid = conn.execute(text("SELECT id FROM regions WHERE name = :r"), {"r": REGION}).scalar()
        if not rid:
            print("Регион не найден")
            return
        rid = str(rid)

        # Backup всех районов
        conn.execute(text("DROP TABLE IF EXISTS _dag_all_backup"))
        conn.execute(text("""
            CREATE TEMP TABLE _dag_all_backup AS
            SELECT id, name, geom FROM districts WHERE region_id = :rid AND geom IS NOT NULL
        """), {"rid": rid})

        # Все части 4 районов, кроме главной (самой большой) у каждого
        conn.execute(text("DROP TABLE IF EXISTS _dag_4_fragments"))
        conn.execute(text("""
            CREATE TEMP TABLE _dag_4_fragments AS
            WITH ranked AS (
                SELECT d.id as source_id, d.name as source_name,
                       (dump).geom as piece_geom,
                       ROUND((ST_Area((dump).geom::geography)/1000000)::numeric, 1) as piece_km2,
                       ROW_NUMBER() OVER (PARTITION BY d.id ORDER BY ST_Area((dump).geom::geography) DESC) as rn
                FROM districts d
                JOIN regions r ON d.region_id = r.id,
                LATERAL ST_Dump(d.geom) AS dump
                WHERE r.name = :region AND d.name = ANY(:names)
            )
            SELECT source_id, source_name, piece_geom, piece_km2
            FROM ranked WHERE rn > 1
        """), {"region": REGION, "names": DISTRICTS})

        n_frag = conn.execute(text("SELECT count(*) FROM _dag_4_fragments")).scalar()
        if n_frag == 0:
            print("Осколков для передачи нет.")
            conn.execute(text("DROP TABLE IF EXISTS _dag_all_backup"))
            return

        # target_id: район с наибольшей площадью пересечения с осколком (не источник)
        # Сначала пробуем ST_Contains(centroid), если нет — по максимальному пересечению
        conn.execute(text("ALTER TABLE _dag_4_fragments ADD COLUMN target_id uuid"))
        conn.execute(text("""
            UPDATE _dag_4_fragments f SET target_id = (
                SELECT b.id FROM _dag_all_backup b
                WHERE b.id != f.source_id
                  AND ST_Contains(b.geom, ST_Centroid(f.piece_geom))
                ORDER BY ST_Area(b.geom::geography) ASC
                LIMIT 1
            )
        """))
        conn.execute(text("""
            UPDATE _dag_4_fragments f SET target_id = (
                SELECT b.id FROM _dag_all_backup b
                WHERE b.id != f.source_id AND f.target_id IS NULL
                  AND ST_Intersects(b.geom, f.piece_geom)
                ORDER BY ST_Area(ST_Intersection(b.geom, f.piece_geom)::geography) DESC
                LIMIT 1
            )
            WHERE f.target_id IS NULL
        """))

        # Вывод и передача осколков целевым
        rows = conn.execute(text("""
            SELECT f.source_name, b.name as target_name, f.piece_km2
            FROM _dag_4_fragments f
            JOIN _dag_all_backup b ON b.id = f.target_id
            WHERE f.target_id IS NOT NULL
        """)).fetchall()
        for row in rows:
            print(f"  {row[0]} -> {row[1]}: {row[2]} км²")

        conn.execute(text("""
            WITH to_add AS (
                SELECT target_id, ST_Union(piece_geom) AS geom
                FROM _dag_4_fragments WHERE target_id IS NOT NULL
                GROUP BY target_id
            )
            UPDATE districts d SET geom = ST_Multi(ST_MakeValid(ST_Union(d.geom, a.geom)))
            FROM to_add a WHERE d.id = a.target_id
        """))

        # Убрать переданные осколки из источников: оставить только главную часть
        conn.execute(text("""
            WITH main_only AS (
                SELECT d.id,
                       ST_Multi((dump).geom) AS geom
                FROM districts d
                JOIN regions r ON d.region_id = r.id,
                LATERAL ST_Dump(d.geom) AS dump
                WHERE r.name = :region AND d.name = ANY(:names)
                ORDER BY d.id, ST_Area((dump).geom::geography) DESC
            ),
            first_part AS (
                SELECT DISTINCT ON (id) id, geom FROM main_only
            )
            UPDATE districts d SET geom = f.geom
            FROM first_part f WHERE d.id = f.id
        """), {"region": REGION, "names": DISTRICTS})

        conn.execute(text("DROP TABLE IF EXISTS _dag_all_backup"))
        conn.execute(text("DROP TABLE IF EXISTS _dag_4_fragments"))

        conn.execute(text("""
            UPDATE districts d SET geom_simplified = ST_SimplifyPreserveTopology(d.geom, 0.005)
            FROM regions r
            WHERE d.region_id = r.id AND r.name = :region AND d.geom IS NOT NULL
        """), {"region": REGION})

    print("\nГотово. Проверка:")
    with engine.connect() as conn:
        for name in DISTRICTS:
            r = conn.execute(text("""
                SELECT ST_NumGeometries(d.geom), ROUND((ST_Area(d.geom::geography)/1000000)::numeric, 1)
                FROM districts d JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND d.name = :name
            """), {"region": REGION, "name": name}).fetchone()
            print(f"  {name}: {r[0]} частей, {r[1]} км²")


if __name__ == "__main__":
    main()
