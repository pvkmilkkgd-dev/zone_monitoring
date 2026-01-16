#!/usr/bin/env python
"""Проверка правильности сопоставления регионов."""
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


def check_specific_regions(db: Session):
    """Проверяет сопоставление конкретных регионов."""
    print("=== Проверка сопоставления регионов ===\n")
    
    # Примеры регионов для проверки
    test_cases = [
        ("Алтай", "Республика Алтай"),
        ("Бурятия", "Республика Бурятия"),
        ("Тыва", "Республика Тыва"),
    ]
    
    for geojson_name, expected_db_name in test_cases:
        result = db.execute(
            text("SELECT name, name_original FROM regions WHERE name_original = :original"),
            {"original": geojson_name}
        ).first()
        
        if result:
            db_name, original = result
            status = "OK" if db_name == expected_db_name else "WRONG"
            print(f"{status} GeoJSON: '{geojson_name}' -> DB: '{db_name}' (name_original: '{original}')")
            if db_name != expected_db_name:
                print(f"   Expected: '{expected_db_name}'")
        else:
            print(f"NOT FOUND GeoJSON: '{geojson_name}' -> not found in DB")
    
    # Проверяем все регионы из GeoJSON
    print(f"\n=== Полная проверка ===")
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        fc = json.load(f)
    
    matched = 0
    not_matched = 0
    
    for feature in fc.get("features", []):
        geojson_name = get_name(feature.get("properties") or {})
        if not geojson_name:
            continue
            
        result = db.execute(
            text("SELECT name FROM regions WHERE name_original = :original"),
            {"original": geojson_name}
        ).first()
        
        if result:
            matched += 1
        else:
            not_matched += 1
            print(f"  НЕ НАЙДЕН: '{geojson_name}'")
    
    print(f"\nСопоставлено: {matched} из {matched + not_matched}")
    print(f"Не найдено: {not_matched}")


def main():
    db = SessionLocal()
    try:
        check_specific_regions(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
