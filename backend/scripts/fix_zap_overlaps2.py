"""
Проверка ВСЕХ типов пересечений в Запорожской области:
- ST_Overlaps (частичное пересечение)
- ST_Contains/ST_Within (один внутри другого)
- ST_Intersects с ненулевой площадью
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

import sqlalchemy as sa
from sqlalchemy import text
from app.core.config import settings

engine = sa.create_engine(settings.DATABASE_URL)


def main():
    print("=" * 70)
    print("ПРОВЕРКА ПЕРЕСЕЧЕНИЙ В ЗАПОРОЖСКОЙ ОБЛАСТИ")
    print("=" * 70)

    with engine.begin() as conn:
        region_id = conn.execute(text(
            "SELECT id FROM regions WHERE name ILIKE '%Запорож%'"
        )).scalar()

        # Check ALL intersections with area > 0.1 km²
        print("\n--- Все пересечения (площадь > 0.1 km²) ---")
        r = conn.execute(text("""
            SELECT d1.id, d1.name,
                   ROUND((ST_Area(d1.geom::geography)/1e6)::numeric, 1) as a1,
                   d2.id, d2.name,
                   ROUND((ST_Area(d2.geom::geography)/1e6)::numeric, 1) as a2,
                   ROUND((ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1e6)::numeric, 1) as overlap,
                   ST_Overlaps(d1.geom, d2.geom) as overlaps,
                   ST_Contains(d1.geom, d2.geom) as d1_contains_d2,
                   ST_Within(d1.geom, d2.geom) as d1_within_d2
            FROM districts d1
            JOIN districts d2 ON d1.id < d2.id
            WHERE d1.region_id = :rid AND d2.region_id = :rid
              AND d1.geom IS NOT NULL AND d2.geom IS NOT NULL
              AND ST_Intersects(d1.geom, d2.geom)
              AND ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1e6 > 0.1
            ORDER BY overlap DESC
        """), {"rid": str(region_id)})
        rows = r.fetchall()

        if not rows:
            print("  Пересечений нет!")
        else:
            for row in rows:
                rel = ""
                if row[7]:
                    rel = "OVERLAPS"
                elif row[8]:
                    rel = "CONTAINS"
                elif row[9]:
                    rel = "WITHIN"
                else:
                    rel = "INTERSECTS"
                print(f"  {row[1]} ({row[2]} km²) <-> {row[4]} ({row[5]} km²): {row[6]} km² [{rel}]")

            # Fix: cut smaller/newer from larger/older
            print("\n--- Вырезка пересечений ---")
            new_mos = {"Бердянский муниципальный округ", "Мелитопольский муниципальный округ"}
            go_prefixes = {"городской округ"}

            for d1_id, d1_name, a1, d2_id, d2_name, a2, overlap, *_ in rows:
                # Determine cutter and target
                # ГО вырезаются из МО, новые МО вырезаются из старых
                d1_is_go = any(d1_name.startswith(p) for p in go_prefixes)
                d2_is_go = any(d2_name.startswith(p) for p in go_prefixes)
                d1_is_new = d1_name in new_mos
                d2_is_new = d2_name in new_mos

                if d1_is_go and not d2_is_go:
                    cutter_id, cutter_name = str(d1_id), d1_name
                    target_id, target_name = str(d2_id), d2_name
                elif d2_is_go and not d1_is_go:
                    cutter_id, cutter_name = str(d2_id), d2_name
                    target_id, target_name = str(d1_id), d1_name
                elif d1_is_new:
                    cutter_id, cutter_name = str(d1_id), d1_name
                    target_id, target_name = str(d2_id), d2_name
                elif d2_is_new:
                    cutter_id, cutter_name = str(d2_id), d2_name
                    target_id, target_name = str(d1_id), d1_name
                else:
                    # Both old MO: cut smaller from larger
                    if a1 < a2:
                        cutter_id, cutter_name = str(d1_id), d1_name
                        target_id, target_name = str(d2_id), d2_name
                    else:
                        cutter_id, cutter_name = str(d2_id), d2_name
                        target_id, target_name = str(d1_id), d1_name

                before = conn.execute(text("""
                    SELECT ROUND((ST_Area(geom::geography)/1e6)::numeric, 1)
                    FROM districts WHERE id = :id
                """), {"id": target_id}).scalar()

                conn.execute(text("""
                    UPDATE districts
                    SET geom = ST_Multi(ST_MakeValid(
                        ST_CollectionExtract(
                            ST_Difference(
                                (SELECT geom FROM districts WHERE id = :target_id),
                                (SELECT geom FROM districts WHERE id = :cutter_id)
                            ),
                            3
                        )
                    ))
                    WHERE id = :target_id
                """), {"target_id": target_id, "cutter_id": cutter_id})

                after = conn.execute(text("""
                    SELECT ROUND((ST_Area(geom::geography)/1e6)::numeric, 1)
                    FROM districts WHERE id = :id
                """), {"id": target_id}).scalar()

                print(f"  '{cutter_name}' из '{target_name}': {before} -> {after} km²")

            # Verify
            print("\n--- Проверка ---")
            r = conn.execute(text("""
                SELECT d1.name, d2.name,
                       ROUND((ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1e6)::numeric, 1)
                FROM districts d1
                JOIN districts d2 ON d1.id < d2.id
                WHERE d1.region_id = :rid AND d2.region_id = :rid
                  AND d1.geom IS NOT NULL AND d2.geom IS NOT NULL
                  AND ST_Intersects(d1.geom, d2.geom)
                  AND ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1e6 > 0.1
                ORDER BY 3 DESC
            """), {"rid": str(region_id)})
            remaining = r.fetchall()
            if remaining:
                for o in remaining:
                    print(f"  {o[0]} <-> {o[1]}: {o[2]} km²")
            else:
                print("  Пересечений нет!")

    print("\nГотово!")


if __name__ == "__main__":
    main()
