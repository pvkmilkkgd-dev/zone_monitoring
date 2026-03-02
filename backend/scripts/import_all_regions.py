"""
Скрипт для импорта всех 89 регионов РФ.
Использует GADM как основной источник + добавляет недостающие регионы.
"""
import sys
import json
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.core.config import settings

DATA_DIR = Path(__file__).parent / "geodata"


# Полный список 89 регионов РФ с маппингом на GADM NAME_1
ALL_REGIONS = {
    # Республики
    "Республика Адыгея": "Adygey",
    "Республика Алтай": "Gorno-Altay",
    "Республика Башкортостан": "Bashkortostan",
    "Республика Бурятия": "Buryat",
    "Республика Дагестан": "Dagestan",
    "Республика Ингушетия": "Ingush",
    "Кабардино-Балкарская Республика": "Kabardin-Balkar",
    "Республика Калмыкия": "Kalmyk",
    "Карачаево-Черкесская Республика": "Karachay-Cherkess",
    "Республика Карелия": "Karelia",
    "Республика Коми": "Komi",
    "Республика Крым": None,  # Нет в GADM
    "Республика Марий Эл": "Mariy-El",
    "Республика Мордовия": "Mordovia",
    "Республика Саха (Якутия)": "Sakha",
    "Республика Северная Осетия - Алания": "NorthOssetia",
    "Республика Татарстан": "Tatarstan",
    "Республика Тыва": "Tuva",
    "Удмуртская Республика": "Udmurt",
    "Республика Хакасия": "Khakass",
    "Чеченская Республика": "Chechnya",
    "Чувашская Республика": "Chuvash",
    
    # Края
    "Алтайский край": "Altay",
    "Забайкальский край": "Zabaykal'ye",
    "Камчатский край": "Kamchatka",
    "Краснодарский край": "Krasnodar",
    "Красноярский край": "Krasnoyarsk",
    "Пермский край": "Perm'",
    "Приморский край": "Primor'ye",
    "Ставропольский край": "Stavropol'",
    "Хабаровский край": "Khabarovsk",
    
    # Области
    "Амурская область": "Amur",
    "Архангельская область": "Arkhangel'sk",
    "Астраханская область": "Astrakhan'",
    "Белгородская область": "Belgorod",
    "Брянская область": "Bryansk",
    "Владимирская область": "Vladimir",
    "Волгоградская область": "Volgograd",
    "Вологодская область": "Vologda",
    "Воронежская область": "Voronezh",
    "Ивановская область": "Ivanovo",
    "Иркутская область": "Irkutsk",
    "Калининградская область": "Kaliningrad",
    "Калужская область": "Kaluga",
    "Кемеровская область": "Kemerovo",
    "Кировская область": "Kirov",
    "Костромская область": "Kostroma",
    "Курганская область": "Kurgan",
    "Курская область": "Kursk",
    "Ленинградская область": "Leningrad",
    "Липецкая область": "Lipetsk",
    "Магаданская область": "Magadan",
    "Московская область": "Moskva",
    "Мурманская область": "Murmansk",
    "Нижегородская область": "Nizhegorod",
    "Новгородская область": "Novgorod",
    "Новосибирская область": "Novosibirsk",
    "Омская область": "Omsk",
    "Оренбургская область": "Orenburg",
    "Орловская область": "Orel",
    "Пензенская область": "Penza",
    "Псковская область": "Pskov",
    "Ростовская область": "Rostov",
    "Рязанская область": "Ryazan'",
    "Самарская область": "Samara",
    "Саратовская область": "Saratov",
    "Сахалинская область": "Sakhalin",
    "Свердловская область": "Sverdlovsk",
    "Смоленская область": "Smolensk",
    "Тамбовская область": "Tambov",
    "Тверская область": "Tver'",
    "Томская область": "Tomsk",
    "Тульская область": "Tula",
    "Тюменская область": "Tyumen'",
    "Ульяновская область": "Ul'yanovsk",
    "Челябинская область": "Chelyabinsk",
    "Ярославская область": "Yaroslavl'",
    
    # Города федерального значения
    "город Москва": "MoscowCity",
    "город Санкт-Петербург": "CityofSt.Petersburg",
    "город Севастополь": None,  # Нет в GADM
    
    # Автономные округа
    "Ненецкий автономный округ": "Nenets",
    "Ханты-Мансийский автономный округ - Югра": "Khanty-Mansiy",
    "Чукотский автономный округ": "Chukot",
    "Ямало-Ненецкий автономный округ": "Yamal-Nenets",
    
    # Автономная область
    "Еврейская автономная область": "Yevrey",
    
    # Новые регионы (2022) - нет в GADM
    "Донецкая Народная Республика": None,
    "Луганская Народная Республика": None,
    "Запорожская область": None,
    "Херсонская область": None,
}


def normalize_name(name: str) -> str:
    """Нормализовать название для сопоставления."""
    if not name:
        return ""
    name = name.lower().strip()
    replacements = [
        "республика ", " республика", " область", " край",
        " автономный округ", " автономная область", "город ",
        " - ", "(", ")", "ё"
    ]
    for r in replacements:
        name = name.replace(r, "")
    name = name.replace("е", "е")
    return " ".join(name.split()).strip()


def load_gadm_data() -> dict:
    """Загрузить данные GADM."""
    gadm_file = DATA_DIR / "gadm_rus_1.json"
    if not gadm_file.exists():
        raise FileNotFoundError(f"GADM файл не найден: {gadm_file}")
    
    with open(gadm_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Создаём маппинг NAME_1 -> feature
    gadm_map = {}
    for feat in data.get('features', []):
        name = feat['properties'].get('NAME_1', '')
        if name:
            gadm_map[name] = feat
    
    return gadm_map


def load_excel_names(excel_path: str) -> dict:
    """Загрузить официальные названия из Excel."""
    df = pd.read_excel(excel_path)
    df.columns = ['region_name', 'district_name', 'admin_center']
    
    excel_names = {}
    for name in df['region_name'].unique():
        norm = normalize_name(name)
        excel_names[norm] = name
    
    return excel_names


def main():
    excel_path = r"C:\Users\Lucky\Downloads\123.xlsx"
    
    print("=" * 60)
    print("ИМПОРТ ВСЕХ 89 РЕГИОНОВ РФ")
    print("=" * 60)
    
    engine = create_engine(settings.DATABASE_URL)
    
    # Загружаем GADM данные
    print("\n1. Загрузка GADM данных...")
    gadm_map = load_gadm_data()
    print(f"   Регионов в GADM: {len(gadm_map)}")
    
    # Загружаем Excel названия
    print("\n2. Загрузка названий из Excel...")
    excel_names = load_excel_names(excel_path)
    print(f"   Регионов в Excel: {len(excel_names)}")
    
    # Импортируем
    print(f"\n3. Импорт {len(ALL_REGIONS)} регионов...")
    
    with engine.connect() as conn:
        # Очищаем таблицу
        conn.execute(text("TRUNCATE TABLE regions CASCADE"))
        conn.commit()
        print("   Таблица regions очищена")
        
        imported_with_geom = 0
        imported_without_geom = 0
        
        for standard_name, gadm_name in ALL_REGIONS.items():
            # Используем стандартное название
            # (Excel названия используются только для районов)
            final_name = standard_name
            
            if gadm_name and gadm_name in gadm_map:
                # Есть в GADM - импортируем с геометрией
                feat = gadm_map[gadm_name]
                geom = feat.get('geometry')
                props = feat.get('properties', {})
                geom_json = json.dumps(geom, ensure_ascii=False)
                
                sql = text("""
                    INSERT INTO regions (id, name, name_original, code, geom, geom_simplified, bbox, created_at, updated_at, is_active)
                    VALUES (
                        gen_random_uuid(),
                        :name,
                        :name_original,
                        :code,
                        ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)), 3)),
                        ST_SimplifyPreserveTopology(
                            ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)), 3)),
                            0.01
                        ),
                        ST_Envelope(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))),
                        NOW(),
                        NOW(),
                        true
                    )
                """)
                
                try:
                    conn.execute(sql, {
                        'name': final_name,
                        'name_original': gadm_name,
                        'code': props.get('GID_1', f'GADM_{gadm_name}'),
                        'geom': geom_json
                    })
                    conn.commit()
                    imported_with_geom += 1
                    print(f"   + {final_name} [с геометрией]")
                except Exception as e:
                    conn.rollback()
                    print(f"   ! {final_name} ОШИБКА: {e}")
                    # Вставляем без геометрии
                    sql2 = text("""
                        INSERT INTO regions (id, name, name_original, code, created_at, updated_at, is_active)
                        VALUES (gen_random_uuid(), :name, :name_original, :code, NOW(), NOW(), true)
                    """)
                    conn.execute(sql2, {
                        'name': final_name,
                        'name_original': standard_name,
                        'code': f'NOGEOM_{standard_name[:20]}'
                    })
                    conn.commit()
                    imported_without_geom += 1
            else:
                # Нет в GADM - импортируем без геометрии
                sql = text("""
                    INSERT INTO regions (id, name, name_original, code, created_at, updated_at, is_active)
                    VALUES (gen_random_uuid(), :name, :name_original, :code, NOW(), NOW(), true)
                """)
                conn.execute(sql, {
                    'name': final_name,
                    'name_original': standard_name,
                    'code': f'NOGEOM_{standard_name[:20]}'
                })
                conn.commit()
                imported_without_geom += 1
                print(f"   + {final_name} [БЕЗ геометрии - нет в GADM]")
    
    total = imported_with_geom + imported_without_geom
    print(f"\n{'=' * 60}")
    print(f"ИМПОРТ ЗАВЕРШЁН!")
    print(f"   Всего регионов: {total}")
    print(f"   С геометрией: {imported_with_geom}")
    print(f"   Без геометрии: {imported_without_geom}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
