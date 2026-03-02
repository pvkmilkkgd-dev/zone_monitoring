"""Диагностика карты Москвы: площади, дубликаты, пробелы."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)

with ENGINE.connect() as c:
    rid = c.execute(text("SELECT id FROM regions WHERE name = 'город Москва'")).scalar()
    if not rid:
        print("Регион Москва не найден")
        sys.exit(1)
    rid = str(rid)

    # Все районы: имя, площадь, кол-во точек
    rows = c.execute(text("""
        SELECT name, ROUND(ST_Area(geom::geography)/1e6) as km2, ST_NPoints(geom) as pts
        FROM districts WHERE region_id = :rid AND geom IS NOT NULL
        ORDER BY ST_Area(geom::geography) DESC
    """), {'rid': rid}).fetchall()

    total_area = sum(r[1] or 0 for r in rows)
    print(f"Районов: {len(rows)}")
    print(f"Суммарная площадь: {total_area} km2 (Москва ~2561 km2)")
    print("\nТоп-15 по площади:")
    for name, km2, pts in rows[:15]:
        print(f"  {km2} km2  {pts} pts  {name}")
    print("\nМинимальные по площади (возможные артефакты):")
    for name, km2, pts in rows[-15:]:
        print(f"  {km2} km2  {pts} pts  {name}")

    # Проверка: объединение всех геометрий — одна ли связная область
    union = c.execute(text("""
        SELECT ST_Union(geom) FROM districts WHERE region_id = :rid AND geom IS NOT NULL
    """), {'rid': rid}).scalar()
    if union:
        num_geoms = c.execute(text("SELECT ST_NumGeometries(:g)"), {'g': union}).scalar()
        area_union = c.execute(text("SELECT ROUND(ST_Area(:g::geography)/1e6)"), {'g': union}).scalar()
        print(f"\nОбъединение всех районов: {num_geoms} полигонов, площадь {area_union} km2")

    # Дубликаты имён
    dupes = c.execute(text("""
        SELECT name, COUNT(*) FROM districts WHERE region_id = :rid GROUP BY name HAVING COUNT(*) > 1
    """), {'rid': rid}).fetchall()
    if dupes:
        print("\nДубликаты имён:", dupes)
