# -*- coding: utf-8 -*-
"""
Убрать осколок и тонкую полоску у городского округа г. Кизляр.
Если геометрия — один полигон с «гантелью» (основная часть + полоска + осколок),
используем отрицательный буфер чтобы отсечь тонкую связь, затем оставляем главную часть.
"""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
REGION = "Республика Дагестан"
NAME = "городской округ г. Кизляр"

def main():
    with engine.begin() as conn:
        # Отрицательный буфер отсекает тонкую полоску; берём самую большую часть
        for buffer_m in [30, 50, 100, 150]:
            result = conn.execute(text("""
                WITH orig AS (
                    SELECT d.id, d.geom
                    FROM districts d JOIN regions r ON d.region_id = r.id
                    WHERE r.name = :region AND d.name = :name
                ),
                buffered AS (
                    SELECT id, ST_CollectionExtract(ST_MakeValid(
                        ST_Buffer(geom::geography, :buf)::geometry
                    ), 3) AS geom
                    FROM orig
                ),
                parts AS (
                    SELECT id, (dump).geom AS part_geom,
                           ST_Area((dump).geom::geography) AS area
                    FROM buffered, LATERAL ST_Dump(geom) AS dump
                    WHERE NOT ST_IsEmpty(buffered.geom)
                ),
                best AS (
                    SELECT id, ST_Multi(part_geom) AS geom
                    FROM (SELECT *, ROW_NUMBER() OVER (ORDER BY area DESC) rn FROM parts) x
                    WHERE rn = 1
                )
                SELECT geom FROM best
            """), {"region": REGION, "name": NAME, "buf": -buffer_m}).fetchone()
            if result and result[0]:
                new_geom = result[0]
                area = conn.execute(text("""
                    SELECT ROUND((ST_Area(CAST(:g AS geography))/1000000)::numeric, 1)
                """), {"g": new_geom}).scalar()
                print(f"Buffer -{buffer_m}m: {area} km2")
                if area and area > 20:
                    conn.execute(text("""
                        UPDATE districts d SET
                            geom = :geom,
                            geom_simplified = ST_SimplifyPreserveTopology(:geom, 0.005)
                        FROM regions r
                        WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
                    """), {"geom": new_geom, "region": REGION, "name": NAME})
                    print(f"OK: оставлена главная часть {area} км2")
                    return
        print("Не удалось отсечь полоску буфером, пробуем ST_ConcaveHull...")
        result = conn.execute(text("""
            WITH orig AS (
                SELECT d.id, d.geom
                FROM districts d JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND d.name = :name
            ),
            hull AS (
                SELECT id, ST_Multi(ST_ConcaveHull(geom, 0.9, true)) AS geom
                FROM orig
            )
            SELECT id, geom FROM hull WHERE NOT ST_IsEmpty(geom)
        """), {"region": REGION, "name": NAME}).fetchone()
        if result:
            conn.execute(text("""
                UPDATE districts d SET
                    geom = :geom,
                    geom_simplified = ST_SimplifyPreserveTopology(:geom, 0.005)
                FROM regions r
                WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
            """), {"geom": result[1], "region": REGION, "name": NAME})
            print("OK: применен ConcaveHull")
        else:
            print("Не удалось обработать")

if __name__ == "__main__":
    main()
