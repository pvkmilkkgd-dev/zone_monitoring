#!/usr/bin/env python
"""Синхронизация регионов с сохранением исходных названий из GeoJSON."""
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


def sync_regions(db: Session):
    """Синхронизирует регионы из GeoJSON в БД с сохранением исходных названий."""
    if not GEOJSON_PATH.exists():
        print(f"ERROR: GeoJSON file not found: {GEOJSON_PATH}")
        return

    print("=== Синхронизация регионов с исходными названиями ===\n")

    # Загружаем GeoJSON
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        fc = json.load(f)

    features = fc.get("features", [])
    print(f"Регионов в GeoJSON: {len(features)}")

    imported = 0
    updated = 0
    skipped = 0
    matched = 0

    for feature in features:
        props = feature.get("properties") or {}
        geojson_name = get_name(props)
        geometry = feature.get("geometry")

        if not geojson_name or not geometry:
            skipped += 1
            continue

        # Преобразуем geometry в JSON строку
        geom_json = json.dumps(geometry, ensure_ascii=False)

        # Проверяем, существует ли регион с таким исходным названием
        existing_by_original = db.execute(
            text("SELECT id, name FROM regions WHERE name_original = :name LIMIT 1"),
            {"name": geojson_name},
        ).first()

        # Проверяем, существует ли регион с таким официальным названием
        existing_by_name = db.execute(
            text("SELECT id, name FROM regions WHERE name = :name LIMIT 1"),
            {"name": geojson_name},
        ).first()

        try:
            if existing_by_original:
                # Регион уже существует с таким исходным названием - обновляем геометрию
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
                        WHERE name_original = :name
                        """
                    ),
                    {"name": geojson_name, "geom": geom_json},
                )
                updated += 1
                matched += 1
            elif existing_by_name:
                # Регион существует с таким названием, но name_original не заполнен - обновляем
                db.execute(
                    text(
                        """
                        UPDATE regions
                        SET name_original = :original_name,
                            geom = ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326),
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
                    {"name": geojson_name, "original_name": geojson_name, "geom": geom_json},
                )
                updated += 1
                matched += 1
            else:
                # Региона нет - создаем новый с обоими названиями
                db.execute(
                    text(
                        """
                        INSERT INTO regions (id, name, name_original, geom, geom_simplified, bbox, created_at, updated_at, is_active)
                        VALUES (
                            gen_random_uuid(), 
                            :name,
                            :original_name,
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
                    {"name": geojson_name, "original_name": geojson_name, "geom": geom_json},
                )
                imported += 1
        except Exception as e:
            print(f"Ошибка при обработке региона '{geojson_name}': {e}")
            skipped += 1
            db.rollback()
            continue

    db.commit()
    print(f"\n=== Результаты синхронизации ===")
    print(f"Импортировано новых: {imported}")
    print(f"Обновлено существующих: {updated}")
    print(f"Сопоставлено по исходным названиям: {matched}")
    print(f"Пропущено (ошибки/без имени/геометрии): {skipped}")

    # Проверяем финальное количество
    total = db.execute(text("SELECT COUNT(*) FROM regions")).scalar()
    with_original = db.execute(text("SELECT COUNT(*) FROM regions WHERE name_original IS NOT NULL")).scalar()
    print(f"\nВсего регионов в БД: {total}")
    print(f"Регионов с исходным названием: {with_original}")


def main():
    db = SessionLocal()
    try:
        sync_regions(db)
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
