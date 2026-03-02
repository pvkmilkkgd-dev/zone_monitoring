"""
Полное исправление геометрии ДНР из GADM-бэкапа.

Шаги:
1. Восстановить ВСЕ 30 районов из geom_gadm_backup
2. Склеить 2 кусочка Харцызска (ST_Union)
3. Перенести отделённые фрагменты в правильных соседей:
   - Артемовский (2 части): маленькую -> Ясиноватский
   - Торез (2 части): маленькую -> Шахтерский
   - Красноармейский (3 части): 2 маленькие -> Кураховский
4. Вырезать городские округа из муниципальных:
   - Докучаевск из Волновахского
   - Иловайск из Амвросиевского
"""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

import sqlalchemy as sa
from sqlalchemy import text
from app.core.config import settings

engine = sa.create_engine(settings.DATABASE_URL)


def get_district_id(conn, name_part):
    """Get district ID by name pattern (for DNR region)."""
    r = conn.execute(text("""
        SELECT d.id FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name ILIKE '%Донецк%' AND d.name ILIKE :pat
    """), {"pat": f"%{name_part}%"})
    row = r.fetchone()
    if not row:
        print(f"  [!] НЕ НАЙДЕН район: {name_part}")
        return None
    return str(row[0])


def print_district(conn, district_id, label=""):
    """Print district geometry info."""
    r = conn.execute(text("""
        SELECT d.name,
               ST_NPoints(d.geom) as pts,
               ROUND((ST_Area(d.geom::geography)/1e6)::numeric, 1) as area,
               ST_NumGeometries(d.geom) as parts
        FROM districts d WHERE d.id = :did
    """), {"did": district_id})
    row = r.fetchone()
    if row:
        print(f"  {label}{row[0]}: {row[1]} pts, {row[2]} km², {row[3]} частей")


def main():
    print("=" * 70)
    print("ИСПРАВЛЕНИЕ ГЕОМЕТРИИ ДНР (только из GADM-бэкапа)")
    print("=" * 70)

    with engine.begin() as conn:
        # ============================================================
        # ШАГ 1: Восстановить ВСЕ из GADM-бэкапа
        # ============================================================
        print("\n--- Шаг 1: Восстановление из GADM-бэкапа ---")
        r = conn.execute(text("""
            UPDATE districts d
            SET geom = d.geom_gadm_backup
            FROM regions r
            WHERE d.region_id = r.id
              AND r.name ILIKE '%Донецк%'
              AND d.geom_gadm_backup IS NOT NULL
        """))
        print(f"  Восстановлено: {r.rowcount} районов")

        # Verify
        r = conn.execute(text("""
            SELECT COUNT(*), SUM(CASE WHEN d.geom IS NOT NULL THEN 1 ELSE 0 END)
            FROM districts d
            JOIN regions r ON d.region_id = r.id
            WHERE r.name ILIKE '%Донецк%'
        """))
        total, with_geom = r.fetchone()
        print(f"  Всего: {total}, с геометрией: {with_geom}")

        # ============================================================
        # ШАГ 2: Склеить 2 кусочка Харцызска
        # ============================================================
        print("\n--- Шаг 2: Склейка Харцызска (2 GADM-кусочка) ---")
        khartsyzsk_id = get_district_id(conn, "Харцызск")
        if khartsyzsk_id:
            print_district(conn, khartsyzsk_id, "ДО:  ")
            conn.execute(text("""
                UPDATE districts
                SET geom = ST_Multi(ST_MakeValid(ST_Union(
                    (SELECT (ST_Dump(geom)).geom FROM districts WHERE id = :did LIMIT 1),
                    (SELECT (ST_Dump(geom)).geom FROM districts WHERE id = :did OFFSET 1 LIMIT 1)
                )))
                WHERE id = :did
            """), {"did": khartsyzsk_id})
            # Actually, simpler approach: ST_Union of all geometries in the collection
            conn.execute(text("""
                UPDATE districts
                SET geom = ST_Multi(ST_MakeValid(
                    ST_UnaryUnion(geom)
                ))
                WHERE id = :did
            """), {"did": khartsyzsk_id})
            print_district(conn, khartsyzsk_id, "ПОСЛЕ: ")

        # ============================================================
        # ШАГ 3: Перенос фрагментов в правильных соседей
        # ============================================================
        print("\n--- Шаг 3: Перенос отделённых фрагментов ---")

        # Список: (источник, приёмник)
        # Из каждого источника берём все части, кроме самой большой, и
        # переносим в приёмник через ST_Union
        fragment_transfers = [
            ("Артемовский муниципальный", "Ясиноватский муниципальный"),
            ("Торез", "Шахтерский муниципальный"),
            ("Красноармейский муниципальный", "Кураховский муниципальный"),
        ]

        for src_name, dst_name in fragment_transfers:
            src_id = get_district_id(conn, src_name)
            dst_id = get_district_id(conn, dst_name)
            if not src_id or not dst_id:
                continue

            # Check how many parts
            r = conn.execute(text("""
                SELECT ST_NumGeometries(geom) FROM districts WHERE id = :did
            """), {"did": src_id})
            num_parts = r.scalar()
            if num_parts is None or num_parts <= 1:
                print(f"  {src_name}: {num_parts} часть, пропуск")
                continue

            print(f"\n  Перенос из '{src_name}' ({num_parts} частей) -> '{dst_name}'")
            print_district(conn, src_id, "  SRC ДО:  ")
            print_district(conn, dst_id, "  DST ДО:  ")

            # Extract the largest part for the source (keep it)
            # and merge the rest into the destination
            conn.execute(text("""
                WITH parts AS (
                    SELECT (ST_Dump(geom)).geom AS part
                    FROM districts WHERE id = :src_id
                ),
                ranked AS (
                    SELECT part, ROW_NUMBER() OVER (ORDER BY ST_Area(part::geography) DESC) as rn
                    FROM parts
                ),
                largest AS (
                    SELECT part FROM ranked WHERE rn = 1
                ),
                fragments AS (
                    SELECT ST_Union(part) as frag FROM ranked WHERE rn > 1
                )
                UPDATE districts
                SET geom = ST_Multi(ST_MakeValid(
                    ST_Union(
                        districts.geom,
                        (SELECT frag FROM fragments)
                    )
                ))
                WHERE id = :dst_id
                  AND (SELECT frag FROM fragments) IS NOT NULL
            """), {"src_id": src_id, "dst_id": dst_id})

            # Keep only the largest part in the source
            conn.execute(text("""
                WITH parts AS (
                    SELECT (ST_Dump(geom_gadm_backup)).geom AS part
                    FROM districts WHERE id = :src_id
                ),
                ranked AS (
                    SELECT part, ROW_NUMBER() OVER (ORDER BY ST_Area(part::geography) DESC) as rn
                    FROM parts
                )
                UPDATE districts
                SET geom = ST_Multi(ST_MakeValid(
                    (SELECT part FROM ranked WHERE rn = 1)
                ))
                WHERE id = :src_id
            """), {"src_id": src_id})

            print_district(conn, src_id, "  SRC ПОСЛЕ: ")
            print_district(conn, dst_id, "  DST ПОСЛЕ: ")

        # ============================================================
        # ШАГ 4: Вырезать города из муниципальных округов
        # ============================================================
        print("\n--- Шаг 4: Вырезка городов из МО ---")

        city_cuts = [
            ("Докучаевск", "Волновахский муниципальный"),
            ("Иловайск", "Амвросиевский муниципальный"),
        ]

        for city_name, mo_name in city_cuts:
            city_id = get_district_id(conn, city_name)
            mo_id = get_district_id(conn, mo_name)
            if not city_id or not mo_id:
                continue

            # Check overlap
            r = conn.execute(text("""
                SELECT ST_Intersects(
                    (SELECT geom FROM districts WHERE id = :city_id),
                    (SELECT geom FROM districts WHERE id = :mo_id)
                )
            """), {"city_id": city_id, "mo_id": mo_id})
            intersects = r.scalar()

            if not intersects:
                print(f"  {city_name} не пересекается с {mo_name}, пропуск")
                continue

            print(f"\n  Вырезка '{city_name}' из '{mo_name}'")
            print_district(conn, mo_id, "  МО ДО:  ")

            conn.execute(text("""
                UPDATE districts
                SET geom = ST_Multi(ST_MakeValid(
                    ST_CollectionExtract(
                        ST_Difference(
                            (SELECT geom FROM districts WHERE id = :mo_id),
                            (SELECT geom FROM districts WHERE id = :city_id)
                        ),
                        3
                    )
                ))
                WHERE id = :mo_id
            """), {"mo_id": mo_id, "city_id": city_id})

            print_district(conn, mo_id, "  МО ПОСЛЕ: ")

        # ============================================================
        # ФИНАЛ: Общая статистика
        # ============================================================
        print("\n" + "=" * 70)
        print("ИТОГОВАЯ СТАТИСТИКА")
        print("=" * 70)

        r = conn.execute(text("""
            SELECT d.name,
                   ST_NPoints(d.geom) as pts,
                   ROUND((ST_Area(d.geom::geography)/1e6)::numeric, 1) as area,
                   ST_NumGeometries(d.geom) as parts
            FROM districts d
            JOIN regions r ON d.region_id = r.id
            WHERE r.name ILIKE '%Донецк%'
            ORDER BY d.name
        """))
        rows = r.fetchall()
        total_area = 0.0
        for row in rows:
            area = float(row[2]) if row[2] else 0
            total_area += area
            flag = ""
            if row[1] is None or row[1] == 0:
                flag = " [!!! НЕТ ГЕОМЕТРИИ]"
            elif row[3] and row[3] > 1:
                flag = f" [MultiPolygon: {row[3]} частей]"
            print(f"  {row[0]:<45} {row[1] or 0:>6} pts  {area:>8.1f} km²{flag}")
        print(f"\n  ИТОГО ПЛОЩАДЬ: {total_area:.1f} km²")

        # Check overlaps
        print("\n--- Проверка пересечений ---")
        r = conn.execute(text("""
            SELECT d1.name, d2.name,
                   ROUND((ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1e6)::numeric, 1) as overlap_km2
            FROM districts d1
            JOIN districts d2 ON d1.id < d2.id
            JOIN regions r1 ON d1.region_id = r1.id
            JOIN regions r2 ON d2.region_id = r2.id
            WHERE r1.name ILIKE '%Донецк%'
              AND r2.name ILIKE '%Донецк%'
              AND ST_Overlaps(d1.geom, d2.geom)
              AND ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1e6 > 0.1
            ORDER BY overlap_km2 DESC
            LIMIT 20
        """))
        overlaps = r.fetchall()
        if overlaps:
            for o in overlaps:
                print(f"  {o[0]} <-> {o[1]}: {o[2]} km²")
        else:
            print("  Пересечений нет!")

        print("\nГотово!")


if __name__ == "__main__":
    main()
