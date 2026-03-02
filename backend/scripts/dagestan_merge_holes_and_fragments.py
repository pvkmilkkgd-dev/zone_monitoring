# -*- coding: utf-8 -*-
"""
Перераспределить дыры и мелкие осколки районов Дагестана:
не удалять, а объединять с тем районом, в котором они находятся (ST_Contains).
Запускать после загрузки геометрий из Overpass (до или вместо простого удаления).
"""
import sys
import io
import sqlalchemy as sa
from sqlalchemy import text

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

engine = sa.create_engine("postgresql+psycopg://zone_user:zone_password@localhost:5432/zone_monitoring")
REGION = "Республика Дагестан"
MIN_FRAGMENT_KM2 = 5.0  # части меньше — передаём в район, в котором лежат


def main():
    with engine.begin() as conn:
        rid = conn.execute(
            text("SELECT id FROM regions WHERE name = :r"), {"r": REGION}
        ).scalar()
        if not rid:
            print("Регион не найден")
            return

        # 1) Резервная копия текущих геометрий
        conn.execute(text("DROP TABLE IF EXISTS _dag_backup"))
        conn.execute(text("""
            CREATE TEMP TABLE _dag_backup AS
            SELECT id, geom FROM districts WHERE region_id = :rid
        """), {"rid": rid})

        # 2) Собираем дыры и мелкие фрагменты: (source_id, piece_geom)
        conn.execute(text("DROP TABLE IF EXISTS _dag_pieces"))
        conn.execute(text("""
            CREATE TEMP TABLE _dag_pieces (
                source_id uuid,
                piece_geom geometry,
                target_id uuid
            )
        """))
        # Дыры: для каждого полигона все внутренние кольца как отдельные полигоны
        conn.execute(text("""
            INSERT INTO _dag_pieces (source_id, piece_geom)
            SELECT b.id, ST_SetSRID(ST_MakePolygon(ST_InteriorRingN(poly.geom, i)), 4326)
            FROM _dag_backup b,
                 LATERAL ST_Dump(b.geom) AS poly(path, geom),
                 LATERAL generate_series(1, ST_NumInteriorRings(poly.geom)) AS i
            WHERE ST_NumInteriorRings(poly.geom) >= 1
        """))
        n_holes = conn.execute(text("SELECT count(*) FROM _dag_pieces")).scalar()

        # Мелкие фрагменты (полигоны с площадью < MIN)
        conn.execute(text("""
            INSERT INTO _dag_pieces (source_id, piece_geom)
            SELECT b.id, poly.geom
            FROM _dag_backup b, LATERAL ST_Dump(b.geom) AS poly(path, geom)
            WHERE ST_Area(poly.geom::geography) / 1000000 < :min_km2
        """), {"min_km2": MIN_FRAGMENT_KM2})
        n_pieces = conn.execute(text("SELECT count(*) FROM _dag_pieces")).scalar()
        print(f"Всего кусков (дыры + мелкие фрагменты): {n_pieces} (из них дыр: {n_holes})")

        if n_pieces == 0:
            print("Нечего перераспределять.")
            conn.execute(text("DROP TABLE IF EXISTS _dag_backup"))
            return

        # 3) Для каждого куска находим район, в котором он лежит (по backup геометрии)
        conn.execute(text("""
            UPDATE _dag_pieces p SET target_id = (
                SELECT b.id FROM _dag_backup b
                WHERE b.id != p.source_id
                  AND ST_Contains(b.geom, p.piece_geom)
                ORDER BY ST_Area(b.geom::geography) ASC
                LIMIT 1
            )
        """))
        # Если не нашли по полному Contains, пробуем по центроиду
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
        unassigned = conn.execute(text("SELECT count(*) FROM _dag_pieces WHERE target_id IS NULL")).scalar()
        assigned_other = conn.execute(text("SELECT count(*) FROM _dag_pieces WHERE target_id IS NOT NULL")).scalar()
        # Оставшиеся без целевого района — возвращаем в свой район (не теряем площадь)
        conn.execute(text("UPDATE _dag_pieces SET target_id = source_id WHERE target_id IS NULL"))
        print(f"Передано в другой район: {assigned_other} кусков, возвращено в свой: {unassigned}")

        # 4) По каждому району: базовая геометрия без дыр и без мелких частей + все куски, приписанные к нему
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
                FROM _dag_pieces WHERE target_id IS NOT NULL
                GROUP BY target_id
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

        conn.execute(text("DROP TABLE IF EXISTS _dag_backup"))
        conn.execute(text("DROP TABLE IF EXISTS _dag_pieces"))

    print("Готово: дыры и осколки объединены с районами, в которых находятся.")
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT d.name, ROUND((ST_Area(d.geom::geography)/1000000)::numeric, 1) AS area,
                   ST_NumGeometries(d.geom) AS parts
            FROM districts d JOIN regions r ON d.region_id = r.id
            WHERE r.name = :region AND d.geom IS NOT NULL
            ORDER BY d.name LIMIT 5
        """), {"region": REGION}).fetchall()
        for r in rows:
            print(f"  {r[0]}: {r[1]} km2, {r[2]} parts")


if __name__ == "__main__":
    main()
