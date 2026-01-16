#!/usr/bin/env python
"""Исправление всех названий регионов на официальные."""
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal


def fix_official_names(db: Session):
    """Исправляет все названия на официальные."""
    print("=== Исправление официальных названий ===\n")
    
    # Получаем все регионы
    regions = db.execute(
        text("SELECT id, name, name_original FROM regions ORDER BY name")
    ).all()
    
    updated = 0
    
    for region in regions:
        region_id = region.id
        current_name = region.name
        name_original = region.name_original
        
        # Если name совпадает с name_original и это короткое название - нужно исправить
        if current_name and name_original and current_name == name_original:
            # Проверяем, является ли это коротким названием
            # Если название не содержит официальных слов - это короткое название
            official_keywords = ["Республика", "Край", "Область", "Автономный", "Округ", "Город"]
            is_short_name = not any(keyword in current_name for keyword in official_keywords)
            
            if is_short_name:
                # Пытаемся восстановить официальное название
                # Для республик добавляем "Республика"
                if current_name in ["Алтай", "Бурятия", "Тыва", "Калмыкия", "Коми", 
                                   "Марий Эл", "Мордовия", "Саха", "Якутия", "Северная Осетия",
                                   "Татарстан", "Хакасия", "Чечня", "Чувашия", "Крым",
                                   "Адыгея", "Башкортостан", "Ингушетия", "Карелия"]:
                    official_name = f"Республика {current_name}"
                    if current_name == "Саха" or current_name == "Якутия":
                        official_name = "Республика Саха (Якутия)"
                    elif current_name == "Северная Осетия":
                        official_name = "Республика Северная Осетия - Алания"
                    elif current_name == "Чечня":
                        official_name = "Чеченская Республика"
                    elif current_name == "Чувашия":
                        official_name = "Чувашская Республика"
                    elif current_name == "Удмуртия":
                        official_name = "Удмуртская Республика"
                else:
                    # Для других типов регионов - пропускаем или ищем вручную
                    print(f"  ПРОПУЩЕН: '{current_name}' - не удалось определить официальное название")
                    continue
                
                try:
                    db.execute(
                        text("UPDATE regions SET name = :official_name WHERE id = :region_id"),
                        {"official_name": official_name, "region_id": region_id}
                    )
                    print(f"  '{current_name}' -> '{official_name}'")
                    updated += 1
                except Exception as e:
                    print(f"Ошибка при обновлении '{current_name}': {e}")
                    db.rollback()
                    continue
    
    db.commit()
    print(f"\n=== Результаты ===")
    print(f"Обновлено названий: {updated}")
    
    # Проверяем финальное состояние
    total = db.execute(text("SELECT COUNT(*) FROM regions")).scalar()
    with_same_name = db.execute(
        text("SELECT COUNT(*) FROM regions WHERE name = name_original AND name IS NOT NULL")
    ).scalar()
    
    print(f"\nВсего регионов: {total}")
    print(f"Регионов где name = name_original (короткие): {with_same_name}")


def main():
    db = SessionLocal()
    try:
        fix_official_names(db)
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
