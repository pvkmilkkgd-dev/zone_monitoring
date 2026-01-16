#!/usr/bin/env python
"""Полное восстановление официальных названий регионов из GeoJSON названий."""
import json
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal

GEOJSON_PATH = Path(__file__).parent.parent / "maps" / "ru" / "regions.geojson"

# Полный маппинг коротких названий из GeoJSON на официальные названия
# Составлен на основе стандартного списка официальных названий регионов России
OFFICIAL_NAMES = {
    # Республики
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
    
    # Края - обычно уже правильные, но на всякий случай
    "Алтайский край": "Алтайский край",
    "Камчатский край": "Камчатский край",
    "Краснодарский край": "Краснодарский край",
    "Красноярский край": "Красноярский край",
    "Пермский край": "Пермский край",
    "Приморский край": "Приморский край",
    "Ставропольский край": "Ставропольский край",
    "Хабаровский край": "Хабаровский край",
    "Забайкальский край": "Забайкальский край",
    
    # Автономные округа
    "Ненецкий АО": "Ненецкий автономный округ",
    "Ханты-Мансийский АО": "Ханты-Мансийский автономный округ - Югра",
    "Чукотский АО": "Чукотский автономный округ",
    "Ямало-Ненецкий АО": "Ямало-Ненецкий автономный округ",
    
    # Области и города - обычно уже правильные
    # Москва, Санкт-Петербург остаются как есть
}


def get_name(props: dict) -> str:
    """Извлекает имя региона из свойств GeoJSON."""
    for key in ("name", "name_ru", "NAME", "NAME_1"):
        if key in props and props[key]:
            return str(props[key]).strip()
    return ""


def build_mapping_from_geojson(db: Session):
    """Строит маппинг name_original -> официальное название из БД."""
    # Загружаем GeoJSON
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        fc = json.load(f)
    
    mapping = {}
    
    for feature in fc.get("features", []):
        geojson_name = get_name(feature.get("properties") or {})
        if not geojson_name:
            continue
        
        # Ищем регион в БД с таким name_original
        result = db.execute(
            text("SELECT name FROM regions WHERE name_original = :original LIMIT 1"),
            {"original": geojson_name}
        ).first()
        
        if result:
            db_name = result.name
            # Если db_name уже официальное (содержит ключевые слова), используем его
            official_keywords = ["Республика", "Край", "Область", "Автономный", "Округ", "Город"]
            if any(keyword in db_name for keyword in official_keywords):
                mapping[geojson_name] = db_name
            else:
                # Иначе пробуем найти в маппинге
                mapping[geojson_name] = OFFICIAL_NAMES.get(geojson_name, db_name)
        else:
            # Если не нашли, используем маппинг
            mapping[geojson_name] = OFFICIAL_NAMES.get(geojson_name, geojson_name)
    
    return mapping


def restore_all_official_names(db: Session):
    """Восстанавливает официальные названия для всех регионов."""
    print("=== Восстановление всех официальных названий ===\n")
    
    # Строим маппинг
    print("Строим маппинг name_original -> официальное название...")
    mapping = build_mapping_from_geojson(db)
    print(f"Создан маппинг для {len(mapping)} регионов\n")
    
    # Получаем все регионы где name = name_original (нужно исправить)
    regions = db.execute(
        text("SELECT id, name, name_original FROM regions WHERE name = name_original ORDER BY name")
    ).all()
    
    updated = 0
    skipped = 0
    
    for region in regions:
        region_id = region.id
        current_name = region.name  # Это же и name_original
        name_original = region.name_original
        
        # Ищем официальное название в маппинге
        official_name = mapping.get(name_original)
        
        if official_name and official_name != current_name:
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
        else:
            skipped += 1
    
    db.commit()
    
    print(f"\n=== Результаты ===")
    print(f"Обновлено названий: {updated}")
    print(f"Пропущено (уже официальные или нет маппинга): {skipped}")
    
    # Проверяем финальное состояние
    total = db.execute(text("SELECT COUNT(*) FROM regions")).scalar()
    with_short_names = db.execute(
        text("SELECT COUNT(*) FROM regions WHERE name = name_original AND name IS NOT NULL")
    ).scalar()
    
    print(f"\nВсего регионов: {total}")
    print(f"Регионов где name = name_original (короткие): {with_short_names}")


def main():
    db = SessionLocal()
    try:
        restore_all_official_names(db)
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
