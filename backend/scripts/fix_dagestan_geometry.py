# -*- coding: utf-8 -*-
"""
Обработка геометрии районов Республики Дагестан:

1. Заполнить дыры — дыры в каждом районе становятся частью этого района (убираем interior rings)
2. Осколки — мелкие куски района A внутри района B: добавить к B, убрать из A
3. Пересечения — при перекрытии двух районов: вырезать из меньшего по площади

Usage:
    python scripts/fix_dagestan_geometry.py
"""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

import sqlalchemy as sa
from sqlalchemy import text
from app.core.config import settings

engine = sa.create_engine(settings.DATABASE_URL)
REGION = "Республика Дагестан"
MIN_FRAGMENT_KM2 = 5.0  # осколки меньше — передаём в район, в котором лежат
MIN_OVERLAP_KM2 = 0.01  # пересечения меньше — игнорируем


def main():
    with engine.connect() as conn:
        rid = conn.execute(text("SELECT id FROM regions WHERE name = :r"), {"r": REGION}).scalar()
        if not rid:
            print("Регион не найден")
            return
        rid = str(rid)

    print("=" * 70)
    print("ОБРАБОТКА ГЕОМЕТРИИ РАЙОНОВ ДАГЕСТАНА")
    print("=" * 70)

    with engine.begin() as conn:
        # --- Шаг 1: Заполнить дыры ---
        print("\n1) Заполнение дыр (interior rings -> часть района)")
        conn.execute(text("DROP TABLE IF EXISTS _dag_backup"))
        conn.execute(text("""
            CREATE TEMP TABLE _dag_backup AS
            SELECT id, geom FROM districts WHERE region_id = :rid AND geom IS NOT NULL
        """), {"rid": rid})

        # Пересобираем геометрию: только внешние кольца (дыры заполняются)
        conn.execute(text("""
            WITH parts_no_holes AS (
                SELECT b.id,
                       ST_MakePolygon(ST_ExteriorRing((dump).geom)) AS geom
                FROM _dag_backup b,
                     LATERAL ST_Dump(b.geom) AS dump
                WHERE ST_GeometryType((dump).geom) = 'ST_Polygon'
            ),
            combined AS (
                SELECT id, ST_Multi(ST_Union(geom)) AS geom
                FROM parts_no_holes
                GROUP BY id
            )
            UPDATE districts d SET geom = c.geom
            FROM combined c
            WHERE d.id = c.id AND d.region_id = :rid
        """), {"rid": rid})

        holes_before = conn.execute(text("""
            SELECT COALESCE(SUM(
                (SELECT COALESCE(SUM(ST_NumInteriorRings(g.geom)), 0)
                 FROM districts d2, LATERAL ST_Dump(d2.geom) AS g WHERE d2.id = d.id)
            ), 0)
            FROM districts d JOIN regions r ON d.region_id = r.id
            WHERE r.name = :region AND d.geom IS NOT NULL
        """), {"region": REGION}).scalar()
        print(f"   Дыр после шага 1: {holes_before}")

        # Обновляем backup для следующих шагов
        conn.execute(text("DELETE FROM _dag_backup"))
        conn.execute(text("""
            INSERT INTO _dag_backup SELECT id, geom FROM districts WHERE region_id = :rid AND geom IS NOT NULL
        """), {"rid": rid})

        # --- Шаг 2: Осколки — куски A внутри B -> добавить к B, убрать из A ---
        print("\n2) Осколки: мелкие куски (< {0} км²) передаём в район, где лежат".format(MIN_FRAGMENT_KM2))
        conn.execute(text("DROP TABLE IF EXISTS _dag_pieces"))
        conn.execute(text("""
            CREATE TEMP TABLE _dag_pieces (
                source_id uuid,
                piece_geom geometry,
                target_id uuid
            )
        """))

        # Мелкие фрагменты (полигоны с площадью < MIN)
        conn.execute(text("""
            INSERT INTO _dag_pieces (source_id, piece_geom)
            SELECT b.id, poly.geom
            FROM _dag_backup b, LATERAL ST_Dump(b.geom) AS poly(path, geom)
            WHERE ST_Area(poly.geom::geography) / 1000000 < :min_km2
        """), {"min_km2": MIN_FRAGMENT_KM2})
        n_pieces = conn.execute(text("SELECT count(*) FROM _dag_pieces")).scalar()

        if n_pieces > 0:
            # Для каждого куска — район, в котором он лежит (не свой)
            conn.execute(text("""
                UPDATE _dag_pieces p SET target_id = (
                    SELECT b.id FROM _dag_backup b
                    WHERE b.id != p.source_id
                      AND ST_Contains(b.geom, p.piece_geom)
                    ORDER BY ST_Area(b.geom::geography) ASC
                    LIMIT 1
                )
            """))
            conn.execute(text("""
                UPDATE _dag_pieces p SET target_id = (
                    SELECT b.id FROM _dag_backup b
                    WHERE b.id != p.source_id AND p.target_id IS NULL
                      AND ST_Contains(b.geom, ST_Centroid(p.piece_geom))
                    ORDER BY ST_Area(b.geom::geography) ASC
                    LIMIT 1
                )
                WHERE p.target_id IS NULL
            """))
            assigned = conn.execute(text("SELECT count(*) FROM _dag_pieces WHERE target_id IS NOT NULL")).scalar()
            conn.execute(text("UPDATE _dag_pieces SET target_id = source_id WHERE target_id IS NULL"))

            # Пересобираем: базовая геометрия без мелких частей + куски, приписанные к району
            conn.execute(text("""
                WITH big_parts AS (
                    SELECT b.id, poly.geom
                    FROM _dag_backup b, LATERAL ST_Dump(b.geom) AS poly(path, geom)
                    WHERE ST_Area(poly.geom::geography)/1000000 >= :min_km2
                ),
                base_big AS (
                    SELECT id, ST_Multi(ST_Union(geom)) AS geom FROM big_parts GROUP BY id
                ),
                added AS (
                    SELECT target_id AS id, ST_Union(piece_geom) AS geom
                    FROM _dag_pieces GROUP BY target_id
                ),
                combined AS (
                    SELECT COALESCE(bb.id, a.id) AS id,
                      ST_Multi(ST_MakeValid(ST_Union(
                        COALESCE(bb.geom, ST_GeomFromText('MULTIPOLYGON EMPTY', 4326)),
                        COALESCE(a.geom, ST_GeomFromText('POLYGON EMPTY', 4326))
                      ))) AS geom
                    FROM base_big bb
                    FULL OUTER JOIN added a ON bb.id = a.id
                ),
                fallback AS (
                    SELECT DISTINCT ON (b.id) b.id, ST_Multi(poly.geom) AS geom
                    FROM _dag_backup b, LATERAL ST_Dump(b.geom) AS poly(path, geom)
                    ORDER BY b.id, ST_Area(poly.geom::geography) DESC
                )
                UPDATE districts d SET geom = COALESCE(
                    (SELECT c.geom FROM combined c WHERE c.id = d.id),
                    (SELECT f.geom FROM fallback f WHERE f.id = d.id)
                )
                WHERE d.region_id = :rid
            """), {"min_km2": MIN_FRAGMENT_KM2, "rid": rid})
            print(f"   Обработано осколков: {n_pieces}, передано в другой район: {assigned}")
        else:
            print("   Мелких осколков нет")

        conn.execute(text("DROP TABLE IF EXISTS _dag_pieces"))

        # --- Шаг 3: Пересечения — вырезать из меньшего района ---
        print("\n3) Пересечения: вырезаем из меньшего по площади")
        overlaps = conn.execute(text("""
            SELECT d1.id, d1.name, d2.id, d2.name,
                   ROUND((ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1e6)::numeric, 1) AS overlap_km2,
                   ROUND((ST_Area(d1.geom::geography)/1e6)::numeric, 1) AS a1,
                   ROUND((ST_Area(d2.geom::geography)/1e6)::numeric, 1) AS a2
            FROM districts d1
            JOIN districts d2 ON d1.id < d2.id
            WHERE d1.region_id = :rid AND d2.region_id = :rid
              AND d1.geom IS NOT NULL AND d2.geom IS NOT NULL
              AND ST_Overlaps(d1.geom, d2.geom)
              AND ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1e6 > :min_overlap
            ORDER BY overlap_km2 DESC
        """), {"rid": rid, "min_overlap": MIN_OVERLAP_KM2}).fetchall()

        for d1_id, d1_name, d2_id, d2_name, overlap_km2, a1, a2 in overlaps:
            # Вырезаем из меньшего
            if a1 <= a2:
                target_id, target_name = str(d1_id), d1_name
                cutter_id = str(d2_id)
            else:
                target_id, target_name = str(d2_id), d2_name
                cutter_id = str(d1_id)

            conn.execute(text("""
                UPDATE districts d SET geom = sub.geom
                FROM (
                    SELECT ST_Multi(ST_MakeValid(
                        ST_CollectionExtract(
                            ST_Difference(d2.geom, c.geom),
                            3
                        )
                    )) AS geom
                    FROM districts d2, districts c
                    WHERE d2.id = :tid AND c.id = :cid
                ) sub
                WHERE d.id = :tid AND NOT ST_IsEmpty(sub.geom)
            """), {"tid": target_id, "cid": cutter_id})
            print(f"   Вырезано из '{target_name}': убрано {overlap_km2} км² пересечения")

        conn.execute(text("DROP TABLE IF EXISTS _dag_backup"))

        # --- Финальный проход: заполнить дыры, появившиеся после вырезки пересечений ---
        print("\n4) Финальное заполнение оставшихся дыр")
        conn.execute(text("""
            WITH parts_no_holes AS (
                SELECT d.id,
                       ST_MakePolygon(ST_ExteriorRing((dump).geom)) AS geom
                FROM districts d,
                     LATERAL ST_Dump(d.geom) AS dump
                WHERE d.region_id = :rid AND d.geom IS NOT NULL
                  AND ST_GeometryType((dump).geom) = 'ST_Polygon'
            ),
            combined AS (
                SELECT id, ST_Multi(ST_Union(geom)) AS geom
                FROM parts_no_holes
                GROUP BY id
            )
            UPDATE districts d SET geom = c.geom
            FROM combined c
            WHERE d.id = c.id AND d.region_id = :rid
        """), {"rid": rid})

    # Обновляем geom_simplified
    print("\n5) Обновление geom_simplified")
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE districts d
            SET geom_simplified = ST_SimplifyPreserveTopology(d.geom, 0.005)
            FROM regions r
            WHERE d.region_id = r.id AND r.name = :region AND d.geom IS NOT NULL
        """), {"region": REGION})

    # Итог
    print("\n--- Итог ---")
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT d.name,
                   ROUND((ST_Area(d.geom::geography)/1000000)::numeric, 1) AS area,
                   ST_NumGeometries(d.geom) AS parts,
                   (SELECT COALESCE(SUM(ST_NumInteriorRings(g.geom)), 0)
                    FROM districts d2, LATERAL ST_Dump(d2.geom) AS g WHERE d2.id = d.id) AS holes
            FROM districts d JOIN regions r ON d.region_id = r.id
            WHERE r.name = :region AND d.geom IS NOT NULL
            ORDER BY d.name
        """), {"region": REGION}).fetchall()
        total_holes = sum(r[3] or 0 for r in rows)
        print(f"   Районов: {len(rows)}, дыр: {total_holes}")
        for r in rows[:8]:
            print(f"   {r[0]}: {r[1]} км², {r[2]} частей, {r[3]} дыр")
        if len(rows) > 8:
            print(f"   ... и ещё {len(rows)-8}")

    print("\nГотово.")


if __name__ == "__main__":
    main()
