#!/usr/bin/env python
"""Проверка названий регионов."""
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal


def main():
    db = SessionLocal()
    try:
        # Проверяем регионы с проблемными названиями
        test_regions = ["Алтай", "Тыва", "Бурятия"]
        
        print("Проверка восстановленных названий:")
        for test_name in test_regions:
            result = db.execute(
                text("SELECT name, name_original FROM regions WHERE name_original = :original"),
                {"original": test_name}
            ).first()
            
            if result:
                print(f"  name_original: '{result.name_original}' -> name: '{result.name}'")
        
        # Показываем примеры всех регионов
        print("\nПримеры всех регионов (первые 10):")
        result = db.execute(
            text("SELECT name, name_original FROM regions ORDER BY name LIMIT 10")
        ).all()
        
        for row in result:
            print(f"  name: '{row.name}', name_original: '{row.name_original}'")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
