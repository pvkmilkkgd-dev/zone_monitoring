#!/usr/bin/env python
"""Сравнение названий регионов в GeoJSON и БД."""
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


def main():
    print("=== Сравнение названий регионов ===\n")

    # Загружаем GeoJSON
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        fc = json.load(f)

    geojson_names = set()
    for feature in fc.get("features", []):
        name = get_name(feature.get("properties") or {})
        if name:
            geojson_names.add(name)

    print(f"Регионов в GeoJSON: {len(geojson_names)}")

    # Получаем названия из БД
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT name FROM regions WHERE name IS NOT NULL"))
        db_names = {row.name for row in result if row.name}
        print(f"Регионов в БД: {len(db_names)}")

        # Показываем примеры различий
        print("\nПримеры названий из GeoJSON:")
        for name in sorted(list(geojson_names))[:10]:
            print(f"  - {name}")

        print("\nПримеры названий из БД:")
        for name in sorted(list(db_names))[:10]:
            print(f"  - {name}")

        # Ищем похожие названия
        print("\n=== Анализ различий ===")
        missing = geojson_names - db_names
        extra = db_names - geojson_names

        print(f"\nНазваний в GeoJSON, но не в БД: {len(missing)}")
        if missing:
            print("Примеры:")
            for name in sorted(list(missing))[:5]:
                print(f"  - {name}")

        print(f"\nНазваний в БД, но не в GeoJSON: {len(extra)}")
        if extra:
            print("Примеры:")
            for name in sorted(list(extra))[:5]:
                print(f"  - {name}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
