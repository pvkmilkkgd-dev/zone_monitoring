#!/usr/bin/env python
"""Предоставление прав и синхронизация таблицы regions."""
import json
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal

GEOJSON_PATH = Path(__file__).parent.parent / "maps" / "ru" / "regions.geojson"


def grant_permissions(db: Session):
    """Предоставляет права на запись в таблицу regions."""
    try:
        print("=== Предоставление прав на запись ===")
        
        # Предоставляем права на INSERT, UPDATE, DELETE
        db.execute(text("GRANT INSERT, UPDATE, DELETE ON regions TO zone_user"))
        
        db.commit()
        print("Права предоставлены успешно")
        return True
    except Exception as e:
        db.rollback()
        print(f"Не удалось предоставить права (может потребоваться суперпользователь): {e}")
        print("Продолжаем синхронизацию...")
        return False


def get_name(props: dict) -> str:
    """Извлекает имя региона из свойств GeoJSON."""
    for key in ("name", "name_ru", "NAME", "NAME_1"):
        if key in props and props[key]:
            return str(props[key]).strip()
    return ""


def sync_regions(db: Session):
    """Синхронизирует регионы из GeoJSON в БД."""
    if not GEOJSON_PATH.exists():
        print(f"ERROR: GeoJSON file not found: {GEOJSON_PATH}")
        return

    print("\n=== Синхронизация регионов из GeoJSON в БД ===\n")

    # Загружаем GeoJSON
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        fc = json.load(f)

    features = fc.get("features", [])
    print(f"Регионов в GeoJSON: {len(features)}")

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

        try:
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
        except Exception as e:
            print(f"Ошибка при обработке региона '{name}': {e}")
            skipped += 1
            db.rollback()
            continue

    db.commit()
    print(f"\n=== Результаты синхронизации ===")
    print(f"Импортировано новых: {imported}")
    print(f"Обновлено существующих: {updated}")
    print(f"Пропущено (ошибки/без имени/геометрии): {skipped}")

    # Проверяем финальное количество
    total = db.execute(text("SELECT COUNT(*) FROM regions")).scalar()
    print(f"\nВсего регионов в БД: {total}")


def main():
    # Пытаемся предоставить права (может не сработать, если нет прав суперпользователя)
    db1 = SessionLocal()
    try:
        grant_permissions(db1)
    except Exception as e:
        db1.rollback()
        print(f"Не удалось предоставить права: {e}")
    finally:
        db1.close()
    
    # Синхронизируем регионы в отдельной сессии
    db2 = SessionLocal()
    try:
        sync_regions(db2)
    except Exception as e:
        db2.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db2.close()


if __name__ == "__main__":
    main()
