#!/usr/bin/env python
"""Очистка названий регионов от лишних символов."""
import re
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal


def clean_name(name: str) -> str:
    """Очищает название от лишних символов."""
    if not name:
        return name
    
    # Убираем пробелы в начале и конце
    name = name.strip()
    
    # Заменяем множественные пробелы на одинарные
    name = re.sub(r'\s+', ' ', name)
    
    # Убираем пробелы вокруг тире (оставляем пробел только после тире)
    name = re.sub(r'\s*-\s*', ' - ', name)
    name = re.sub(r'\s*—\s*', ' — ', name)  # Длинное тире
    
    # Убираем пробелы вокруг скобок
    name = re.sub(r'\s*\(\s*', ' (', name)
    name = re.sub(r'\s*\)\s*', ') ', name)
    name = name.strip()
    
    return name


def cleanup_all_names(db: Session):
    """Очищает все названия регионов от лишних символов."""
    print("=== Очистка названий регионов ===\n")
    
    # Получаем все регионы
    regions = db.execute(
        text("SELECT id, name, name_original FROM regions ORDER BY name")
    ).all()
    
    updated_name = 0
    updated_original = 0
    
    for region in regions:
        region_id = region.id
        current_name = region.name
        current_original = region.name_original
        
        # Очищаем name
        cleaned_name = clean_name(current_name) if current_name else current_name
        if cleaned_name != current_name:
            try:
                db.execute(
                    text("UPDATE regions SET name = :clean_name WHERE id = :region_id"),
                    {"clean_name": cleaned_name, "region_id": region_id}
                )
                print(f"  name: '{current_name}' -> '{cleaned_name}'")
                updated_name += 1
            except Exception as e:
                print(f"Ошибка при обновлении name '{current_name}': {e}")
                db.rollback()
                continue
        
        # Очищаем name_original
        cleaned_original = clean_name(current_original) if current_original else current_original
        if cleaned_original != current_original:
            try:
                db.execute(
                    text("UPDATE regions SET name_original = :clean_original WHERE id = :region_id"),
                    {"clean_original": cleaned_original, "region_id": region_id}
                )
                if updated_name == 0:  # Если name не обновлялось, выводим сообщение
                    print(f"  name_original: '{current_original}' -> '{cleaned_original}'")
                updated_original += 1
            except Exception as e:
                print(f"Ошибка при обновлении name_original '{current_original}': {e}")
                db.rollback()
                continue
    
    db.commit()
    
    print(f"\n=== Результаты ===")
    print(f"Обновлено name: {updated_name}")
    print(f"Обновлено name_original: {updated_original}")
    
    # Финальная проверка
    total = db.execute(text("SELECT COUNT(*) FROM regions")).scalar()
    print(f"\nВсего регионов: {total}")


def main():
    db = SessionLocal()
    try:
        cleanup_all_names(db)
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
