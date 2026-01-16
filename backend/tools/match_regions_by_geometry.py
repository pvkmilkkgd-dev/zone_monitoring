#!/usr/bin/env python
"""Сопоставление регионов из GeoJSON с БД по геометрии."""
import json
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal

GEOJSON_PATH = Path(__file__).parent.parent / "maps" / "ru" / "regions.geojson"


def get_name(props: dict) -> str:
    """Извлекает имя региона из свойств GeoJSON."""
    for key in ("name", "name_ru", "NAME", "NAME_1"):
        if key in props and props[key]:
            return str(props[key]).strip()
    return ""


def match_and_update_regions(db: Session):
    """Сопоставляет регионы из GeoJSON с БД по геометрии и обновляет name_original."""
    if not GEOJSON_PATH.exists():
        print(f"ERROR: GeoJSON file not found: {GEOJSON_PATH}")
        return

    print("=== Сопоставление регионов по геометрии ===\n")

    # Загружаем GeoJSON
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        fc = json.load(f)

    features = fc.get("features", [])
    print(f"Регионов в GeoJSON: {len(features)}")

    matched = 0
    updated = 0
    not_found = 0

    for feature in features:
        props = feature.get("properties") or {}
        geojson_name = get_name(props)
        geometry = feature.get("geometry")

        if not geojson_name or not geometry:
            continue

        # Преобразуем geometry в JSON строку
        geom_json = json.dumps(geometry, ensure_ascii=False)

        # Ищем регион с похожей геометрией
        # Используем сравнение по bbox и площади для более надежного сопоставления
        # Сначала пробуем найти по пересечению bbox с более точным сравнением площади
        geojson_geom_sql = "ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))"
        
        # Сначала ищем точное совпадение по bbox и площади
        result = db.execute(
            text(
                f"""
                SELECT id, name, name_original
                FROM regions
                WHERE ST_Intersects(
                    bbox,
                    ST_Envelope({geojson_geom_sql})
                )
                AND ABS(
                    ST_Area(geom) - ST_Area({geojson_geom_sql})
                ) / NULLIF(ST_Area(geom), 0) < 0.15
                ORDER BY ABS(
                    ST_Area(geom) - ST_Area({geojson_geom_sql})
                ) / NULLIF(ST_Area(geom), 0)
                LIMIT 1
                """
            ),
            {"geom": geom_json},
        ).first()
        
        # Если не нашли точное совпадение, пробуем более широкий поиск
        if not result:
            result = db.execute(
                text(
                    f"""
                    SELECT id, name, name_original
                    FROM regions
                    WHERE ST_Intersects(
                        bbox,
                        ST_Envelope({geojson_geom_sql})
                    )
                    AND ABS(
                        ST_Area(geom) - ST_Area({geojson_geom_sql})
                    ) / NULLIF(ST_Area(geom), 0) < 0.25
                    ORDER BY ABS(
                        ST_Area(geom) - ST_Area({geojson_geom_sql})
                    ) / NULLIF(ST_Area(geom), 0)
                    LIMIT 1
                    """
                ),
                {"geom": geom_json},
            ).first()

        if result:
            region_id, db_name, current_original = result
            
            # Если name_original еще не заполнен или отличается
            if not current_original or current_original != geojson_name:
                try:
                    db.execute(
                        text(
                            """
                            UPDATE regions
                            SET name_original = :original_name,
                                updated_at = NOW()
                            WHERE id = :region_id
                            """
                        ),
                        {"original_name": geojson_name, "region_id": region_id},
                    )
                    updated += 1
                    print(f"  {db_name} -> name_original: {geojson_name}")
                except Exception as e:
                    print(f"Ошибка при обновлении региона '{db_name}': {e}")
                    db.rollback()
                    continue
            matched += 1
        else:
            not_found += 1
            print(f"  Не найден: {geojson_name}")

    db.commit()
    
    print(f"\n=== Результаты сопоставления ===")
    print(f"Сопоставлено по геометрии: {matched}")
    print(f"Обновлено name_original: {updated}")
    print(f"Не найдено в БД: {not_found}")

    # Удаляем регионы, которые были добавлены ошибочно (без name_original и с недавним created_at)
    deleted = db.execute(
        text(
            """
            DELETE FROM regions
            WHERE name_original IS NULL
            AND created_at > NOW() - INTERVAL '1 hour'
            RETURNING id
            """
        )
    ).rowcount
    
    db.commit()
    print(f"Удалено ошибочно добавленных регионов: {deleted}")


def main():
    db = SessionLocal()
    try:
        match_and_update_regions(db)
        
        # Проверяем финальное состояние
        total = db.execute(text("SELECT COUNT(*) FROM regions")).scalar()
        with_original = db.execute(text("SELECT COUNT(*) FROM regions WHERE name_original IS NOT NULL")).scalar()
        print(f"\nВсего регионов в БД: {total}")
        print(f"Регионов с name_original: {with_original}")
        
    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
