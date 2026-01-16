#!/usr/bin/env python
"""Синхронизация таблицы regions с GeoJSON файлом."""
import json
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.db.session import SessionLocal

GEOJSON_PATH = Path(__file__).parent.parent / "maps" / "ru" / "regions.geojson"


def get_name(props: dict) -> str:
    """Извлекает имя региона из свойств GeoJSON."""
    for key in ("name", "name_ru", "NAME", "NAME_1"):
        if key in props and props[key]:
            return str(props[key]).strip()
    return ""


def main():
    """Синхронизирует регионы из GeoJSON в БД."""
    if not GEOJSON_PATH.exists():
        print(f"ERROR: GeoJSON file not found: {GEOJSON_PATH}")
        sys.exit(1)

    print("=== Синхронизация регионов из GeoJSON в БД ===\n")

    # Загружаем GeoJSON
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        fc = json.load(f)

    features = fc.get("features", [])
    print(f"Регионов в GeoJSON: {len(features)}")

    db = SessionLocal()
    try:

        imported = 0
        updated = 0
        skipped = 0

        for feature in features:
            props = feature.get("properties") or {}
            name = get_name(props)
            geometry = feature.get("geometry")

            if not name or not geometry:
                skipped += 1
                continue

            # Преобразуем geometry в JSON строку
            geom_json = json.dumps(geometry, ensure_ascii=False)

            # Проверяем, существует ли регион с таким именем
            existing = db.execute(
                text("SELECT id FROM regions WHERE name = :name LIMIT 1"),
                {"name": name},
            ).first()

            if existing:
                # Обновляем существующий регион
                db.execute(
                    text(
                        """
                        UPDATE regions
                        SET geom = ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326),
                            geom_simplified = ST_Multi(
                                ST_CollectionExtract(
                                    ST_SimplifyPreserveTopology(
                                        ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)),
                                        0.05
                                    ),
                                    3
                                )
                            ),
                            bbox = ST_Envelope(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))),
                            updated_at = NOW(),
                            is_active = true
                        WHERE name = :name
                        """
                    ),
                    {"name": name, "geom": geom_json},
                )
                updated += 1
            else:
                # Создаем новый регион
                db.execute(
                    text(
                        """
                        INSERT INTO regions (id, name, geom, geom_simplified, bbox, created_at, updated_at, is_active)
                        VALUES (
                            gen_random_uuid(), 
                            :name, 
                            ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326),
                            ST_Multi(
                                ST_CollectionExtract(
                                    ST_SimplifyPreserveTopology(
                                        ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)),
                                        0.05
                                    ),
                                    3
                                )
                            ),
                            ST_Envelope(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))),
                            NOW(),
                            NOW(),
                            true
                        )
                        """
                    ),
                    {"name": name, "geom": geom_json},
                )
                imported += 1

        db.commit()
        print(f"\n=== Результаты ===")
        print(f"Импортировано новых: {imported}")
        print(f"Обновлено существующих: {updated}")
        print(f"Пропущено (без имени/геометрии): {skipped}")

        # Проверяем финальное количество
        total = db.execute(text("SELECT COUNT(*) FROM regions")).scalar()
        print(f"\nВсего регионов в БД: {total}")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
