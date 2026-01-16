#!/usr/bin/env python
"""Проверка и синхронизация таблицы regions с GeoJSON файлом."""
import json
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal

GEOJSON_PATH = Path(__file__).parent.parent / "maps" / "ru" / "regions.geojson"


def get_region_names_from_geojson() -> set[str]:
    """Извлекает имена регионов из GeoJSON файла."""
    if not GEOJSON_PATH.exists():
        print(f"ERROR: GeoJSON file not found: {GEOJSON_PATH}")
        return set()

    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        fc = json.load(f)

    names = set()
    for feature in fc.get("features", []):
        props = feature.get("properties") or {}
        # Пробуем разные варианты ключей для имени
        for key in ("name", "name_ru", "NAME", "NAME_1"):
            if key in props and props[key]:
                names.add(str(props[key]).strip())
                break

    return names


def get_region_names_from_db(db: Session) -> set[str]:
    """Извлекает имена регионов из базы данных."""
    result = db.execute(text("SELECT DISTINCT name FROM regions WHERE name IS NOT NULL"))
    names = {row.name for row in result if row.name}
    return names


def main():
    print("=== Проверка таблицы regions ===\n")

    # Получаем имена из GeoJSON
    geojson_names = get_region_names_from_geojson()
    print(f"Регионов в GeoJSON файле: {len(geojson_names)}")
    print(f"Первые 10: {sorted(list(geojson_names))[:10]}")

    # Получаем имена из БД
    db = SessionLocal()
    try:
        db_names = get_region_names_from_db(db)
        print(f"\nРегионов в БД: {len(db_names)}")
        print(f"Первые 10: {sorted(list(db_names))[:10]}")

        # Сравниваем
        missing_in_db = geojson_names - db_names
        extra_in_db = db_names - geojson_names

        print(f"\n=== Результаты сравнения ===")
        print(f"Регионов в GeoJSON, но не в БД: {len(missing_in_db)}")
        if missing_in_db:
            print(f"Отсутствуют: {sorted(list(missing_in_db))}")

        print(f"\nРегионов в БД, но не в GeoJSON: {len(extra_in_db)}")
        if extra_in_db:
            print(f"Лишние: {sorted(list(extra_in_db))}")

        if not missing_in_db and not extra_in_db:
            print("\n✓ Все регионы синхронизированы!")

    finally:
        db.close()


if __name__ == "__main__":
    main()
