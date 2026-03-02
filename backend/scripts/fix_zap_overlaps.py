"""
Найти и убрать пересечения в Запорожской области.
Новые МО (Бердянский, Мелитопольский) вырезаются из старых районов,
с которыми пересекаются.
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
    print("ИСПРАВЛЕНИЕ ПЕРЕСЕЧЕНИЙ В ЗАПОРОЖСКОЙ ОБЛАСТИ")
    print("=" * 70)

    with engine.begin() as conn:
        region_id = conn.execute(text(
            "SELECT id FROM regions WHERE name ILIKE '%Запорож%'"
        )).scalar()

        # Find all overlaps
        print("\n--- Текущие пересечения ---")
        r = conn.execute(text("""
            SELECT d1.id, d1.name, d2.id, d2.name,
                   ROUND((ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1e6)::numeric, 1) as overlap_km2
            FROM districts d1
            JOIN districts d2 ON d1.id < d2.id
            WHERE d1.region_id = :rid AND d2.region_id = :rid
              AND d1.geom IS NOT NULL AND d2.geom IS NOT NULL
              AND ST_Overlaps(d1.geom, d2.geom)
              AND ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1e6 > 0.1
            ORDER BY overlap_km2 DESC
        """), {"rid": str(region_id)})
        overlaps = r.fetchall()

        if not overlaps:
            print("  Пересечений нет!")
            return

        for o in overlaps:
            print(f"  {o[1]} <-> {o[3]}: {o[4]} km²")

        # Для каждого пересечения: вырезаем новый МО из старого
        # Бердянский и Мелитопольский МО -- это "правильные" границы районов,
        # старые МО (Приморский, Веселовский и т.д.) были собраны из нескольких
        # GADM районов и включают лишнюю территорию
        new_mos = {"Бердянский муниципальный округ", "Мелитопольский муниципальный округ"}

        print("\n--- Вырезка пересечений ---")
        for d1_id, d1_name, d2_id, d2_name, overlap_km2 in overlaps:
            # Определяем, кого из кого вырезать
            # Вырезаем новый МО из старого (старый уменьшается)
            if d1_name in new_mos:
                cutter_id, cutter_name = str(d1_id), d1_name
                target_id, target_name = str(d2_id), d2_name
            elif d2_name in new_mos:
                cutter_id, cutter_name = str(d2_id), d2_name
                target_id, target_name = str(d1_id), d1_name
            else:
                # Оба старые -- вырезаем меньший из большего
                a1 = conn.execute(text(
                    "SELECT ST_Area(geom::geography)/1e6 FROM districts WHERE id = :id"
                ), {"id": str(d1_id)}).scalar()
                a2 = conn.execute(text(
                    "SELECT ST_Area(geom::geography)/1e6 FROM districts WHERE id = :id"
                ), {"id": str(d2_id)}).scalar()
                if a1 < a2:
                    cutter_id, cutter_name = str(d1_id), d1_name
                    target_id, target_name = str(d2_id), d2_name
                else:
                    cutter_id, cutter_name = str(d2_id), d2_name
                    target_id, target_name = str(d1_id), d1_name

            # Get area before
            before = conn.execute(text("""
                SELECT ROUND((ST_Area(geom::geography)/1e6)::numeric, 1)
                FROM districts WHERE id = :id
            """), {"id": target_id}).scalar()

            # Cut
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

            print(f"  Вырезано '{cutter_name}' из '{target_name}': {before} -> {after} km² (убрано {overlap_km2} km²)")

        # Verify
        print("\n--- Проверка после исправления ---")
        r = conn.execute(text("""
            SELECT d1.name, d2.name,
                   ROUND((ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1e6)::numeric, 1)
            FROM districts d1
            JOIN districts d2 ON d1.id < d2.id
            WHERE d1.region_id = :rid AND d2.region_id = :rid
              AND d1.geom IS NOT NULL AND d2.geom IS NOT NULL
              AND ST_Overlaps(d1.geom, d2.geom)
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
