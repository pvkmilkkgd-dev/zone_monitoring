#!/usr/bin/env python
"""Проверка и исправление официальных названий регионов."""
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal


def verify_official_names(db: Session):
    """Проверяет и исправляет официальные названия."""
    print("=== Проверка официальных названий ===\n")
    
    # Получаем все регионы
    regions = db.execute(
        text("SELECT id, name, name_original FROM regions ORDER BY name")
    ).all()
    
    official_keywords = ["Республика", "Край", "Область", "Автономный", "Округ", "Город"]
    
    problems = []
    correct = 0
    
    for region in regions:
        name = region.name
        name_original = region.name_original
        
        # Проверяем, является ли название официальным
        has_official = any(keyword in name for keyword in official_keywords) if name else False
        
        # Если name = name_original и название не официальное - это проблема
        if name and name_original and name == name_original and not has_official:
            problems.append((region.id, name, name_original))
        else:
            correct += 1
    
    print(f"Правильных названий: {correct}")
    print(f"Проблемных (name = name_original, но не официальное): {len(problems)}")
    
    if problems:
        print("\nПроблемные регионы:")
        for region_id, name, original in problems[:20]:  # Показываем первые 20
            print(f"  ID: {region_id}, name: '{name}', name_original: '{original}'")
        if len(problems) > 20:
            print(f"  ... и еще {len(problems) - 20}")
    
    return problems, correct


def fix_problematic_names(db: Session, problems):
    """Исправляет проблемные названия, оставляя name_original как есть."""
    print(f"\n=== Исправление проблемных названий ===\n")
    
    # Маппинг коротких названий на официальные
    SHORT_TO_OFFICIAL = {
        "Адыгея": "Республика Адыгея",
        "Алтай": "Республика Алтай",
        "Башкортостан": "Республика Башкортостан",
        "Бурятия": "Республика Бурятия",
        "Дагестан": "Республика Дагестан",
        "Ингушетия": "Республика Ингушетия",
        "Кабардино-Балкария": "Кабардино-Балкарская Республика",
        "Калмыкия": "Республика Калмыкия",
        "Карачаево-Черкесия": "Карачаево-Черкесская Республика",
        "Карелия": "Республика Карелия",
        "Коми": "Республика Коми",
        "Крым": "Республика Крым",
        "Марий Эл": "Республика Марий Эл",
        "Мордовия": "Республика Мордовия",
        "Саха": "Республика Саха (Якутия)",
        "Якутия": "Республика Саха (Якутия)",
        "Северная Осетия": "Республика Северная Осетия - Алания",
        "Татарстан": "Республика Татарстан",
        "Тыва": "Республика Тыва",
        "Тува": "Республика Тыва",
        "Удмуртия": "Удмуртская Республика",
        "Хакасия": "Республика Хакасия",
        "Чечня": "Чеченская Республика",
        "Чувашия": "Чувашская Республика",
    }
    
    updated = 0
    
    for region_id, short_name, name_original in problems:
        official_name = SHORT_TO_OFFICIAL.get(short_name)
        
        if official_name:
            try:
                db.execute(
                    text("UPDATE regions SET name = :official_name WHERE id = :region_id"),
                    {"official_name": official_name, "region_id": region_id}
                )
                print(f"  '{short_name}' -> '{official_name}'")
                updated += 1
            except Exception as e:
                print(f"Ошибка при обновлении '{short_name}': {e}")
                db.rollback()
                continue
        else:
            print(f"  ПРОПУЩЕН: '{short_name}' - нет маппинга на официальное название")
    
    db.commit()
    print(f"\nОбновлено: {updated}")
    
    return updated


def main():
    db = SessionLocal()
    try:
        problems, correct = verify_official_names(db)
        
        if problems:
            fix_problematic_names(db, problems)
        
        # Финальная проверка
        total = db.execute(text("SELECT COUNT(*) FROM regions")).scalar()
        with_short = db.execute(
            text("SELECT COUNT(*) FROM regions WHERE name = name_original AND name IS NOT NULL")
        ).scalar()
        
        print(f"\n=== Финальное состояние ===")
        print(f"Всего регионов: {total}")
        print(f"Регионов где name = name_original: {with_short}")
        
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
