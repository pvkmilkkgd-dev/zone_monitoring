#!/usr/bin/env python
"""Нормализация названий регионов к официальным (убирает пробелы вокруг тире и т.д.)."""
import re
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal

# Маппинг неофициальных названий к официальным
OFFICIAL_NAMES_MAP = {
    "Санкт - Петербург": "Санкт-Петербург",
    "Санкт — Петербург": "Санкт-Петербург",
    "Санкт  -  Петербург": "Санкт-Петербург",
    "Санкт- Петербург": "Санкт-Петербург",
    "Санкт -Петербург": "Санкт-Петербург",
    # Добавьте другие неофициальные варианты, если нужно
}


def normalize_name(name: str) -> str:
    """Нормализует название к официальному формату."""
    if not name:
        return name
    
    # Убираем пробелы в начале и конце
    name = name.strip()
    
    # Заменяем различные типы тире на стандартное короткое тире
    name = re.sub(r"[—–]", "-", name)
    
    # Убираем пробелы вокруг тире (важно: именно УБИРАЕМ пробелы)
    name = re.sub(r"\s*-\s*", "-", name)
    
    # Убираем множественные пробелы
    name = re.sub(r"\s+", " ", name)
    
    # Убираем пробелы перед скобками
    name = re.sub(r"\s+\(/", " (", name)
    # Убираем пробелы после скобок
    name = re.sub(r"\)\s+", ") ", name)
    
    # Финальная очистка
    name = name.strip()
    
    # Проверяем маппинг на точное совпадение
    if name in OFFICIAL_NAMES_MAP:
        name = OFFICIAL_NAMES_MAP[name]
    
    return name


def normalize_all_names(db: Session):
    """Нормализует все названия регионов."""
    print("=== Нормализация названий регионов к официальным ===\n")
    
    regions = db.execute(
        text("SELECT id, name, name_original FROM regions ORDER BY name")
    ).all()
    
    updated_name_count = 0
    updated_original_count = 0
    
    for region in regions:
        region_id = region.id
        current_name = region.name
        current_original = region.name_original
        
        # Нормализуем name
        normalized_name = normalize_name(current_name) if current_name else current_name
        
        if normalized_name != current_name:
            try:
                db.execute(
                    text("UPDATE regions SET name = :normalized_name, updated_at = NOW() WHERE id = :region_id"),
                    {"normalized_name": normalized_name, "region_id": region_id}
                )
                print(f"  name: '{current_name}' -> '{normalized_name}'")
                updated_name_count += 1
            except Exception as e:
                print(f"Ошибка при обновлении name '{current_name}': {e}")
                db.rollback()
                continue
        
        # Нормализуем name_original (если нужно)
        normalized_original = normalize_name(current_original) if current_original else current_original
        
        if normalized_original != current_original:
            try:
                db.execute(
                    text("UPDATE regions SET name_original = :normalized_original, updated_at = NOW() WHERE id = :region_id"),
                    {"normalized_original": normalized_original, "region_id": region_id}
                )
                if updated_name_count == 0:  # Если name не обновлялось, выводим сообщение
                    print(f"  name_original: '{current_original}' -> '{normalized_original}'")
                updated_original_count += 1
            except Exception as e:
                print(f"Ошибка при обновлении name_original '{current_original}': {e}")
                db.rollback()
                continue
    
    db.commit()
    
    print(f"\n=== Результаты ===")
    print(f"Обновлено name: {updated_name_count}")
    print(f"Обновлено name_original: {updated_original_count}")
    
    total = db.execute(text("SELECT COUNT(*) FROM regions")).scalar()
    print(f"\nВсего регионов в БД: {total}")
    
    # Показываем примеры названий с тире для проверки
    print("\nПримеры названий с тире:")
    dash_names = db.execute(
        text("SELECT name FROM regions WHERE name LIKE '%-%' ORDER BY name LIMIT 10")
    ).scalars().all()
    for n in dash_names:
        print(f"  - {n}")


def main():
    db = SessionLocal()
    try:
        normalize_all_names(db)
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
