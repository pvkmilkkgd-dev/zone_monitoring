"""
Скрипт для загрузки официальных названий регионов, районов и административных центров РФ
с геометрией из GADM и OpenStreetMap.
"""
import os
import sys
import json
import zipfile
import requests
import pandas as pd
from io import BytesIO
from pathlib import Path
from transliterate import translit

# Добавляем путь к backend для импорта моделей
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.core.config import settings

# Папка для скачанных данных
DATA_DIR = Path(__file__).parent / "geodata"
DATA_DIR.mkdir(exist_ok=True)

# URL для скачивания данных GADM (уровень 1 = регионы, уровень 2 = районы)
GADM_URL = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_RUS_{level}.json.zip"


def download_gadm_data(level: int) -> dict:
    """Скачать данные GADM для указанного уровня."""
    url = GADM_URL.format(level=level)
    cache_file = DATA_DIR / f"gadm_rus_{level}.json"
    
    if cache_file.exists():
        print(f"  Используем кэшированные данные: {cache_file}")
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    print(f"  Скачиваем с {url}...")
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    
    # Распаковываем ZIP
    with zipfile.ZipFile(BytesIO(response.content)) as z:
        # Находим JSON файл в архиве
        json_files = [f for f in z.namelist() if f.endswith('.json')]
        if not json_files:
            raise ValueError("JSON файл не найден в архиве")
        
        with z.open(json_files[0]) as f:
            data = json.load(f)
    
    # Кэшируем
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    
    print(f"  Сохранено в кэш: {cache_file}")
    return data


def load_excel_data(excel_path: str) -> pd.DataFrame:
    """Загрузить данные из Excel файла."""
    df = pd.read_excel(excel_path)
    df.columns = ['region_name', 'district_name', 'admin_center']
    return df


def normalize_name(name: str) -> str:
    """Нормализовать название для сравнения."""
    if not name:
        return ""
    name = name.lower().strip()
    # Удаляем типичные окончания
    replacements = [
        "ая область", "ий край", "ая республика", "республика ", 
        "ий автономный округ", "ая автономная область",
        "ий муниципальный район", "ой городской округ",
        "ий район", "ий округ", "ая", "ий", "ое", "ый"
    ]
    for r in replacements:
        name = name.replace(r, "")
    return name.strip()


# Точный маппинг названий Excel -> GADM
REGION_MAPPING = {
    "Алтайский край": "Altay",
    "Амурская область": "Amur",
    "Архангельская область": "Arkhangel'sk",
    "Астраханская область": "Astrakhan'",
    "Белгородская область": "Belgorod",
    "Брянская область": "Bryansk",
    "Владимирская область": "Vladimir",
    "Волгоградская область": "Volgograd",
    "Вологодская область": "Vologda",
    "Воронежская область": "Voronezh",
    "Еврейская автономная область": "Yevrey",
    "Забайкальский край": "Zabaykal'ye",
    "Ивановская область": "Ivanovo",
    "Иркутская область": "Irkutsk",
    "Калининградская область": "Kaliningrad",
    "Калужская область": "Kaluga",
    "Камчатский край": "Kamchatka",
    "Кемеровская область": "Kemerovo",
    "Кировская область": "Kirov",
    "Костромская область": "Kostroma",
    "Краснодарский край": "Krasnodar",
    "Красноярский край": "Krasnoyarsk",
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
    "Пермский край": "Perm'",
    "Приморский край": "Primor'ye",
    "Псковская область": "Pskov",
    "Ростовская область": "Rostov",
    "Рязанская область": "Ryazan'",
    "Самарская область": "Samara",
    "Саратовская область": "Saratov",
    "Сахалинская область": "Sakhalin",
    "Свердловская область": "Sverdlovsk",
    "Смоленская область": "Smolensk",
    "Ставропольский край": "Stavropol'",
    "Тамбовская область": "Tambov",
    "Тверская область": "Tver'",
    "Томская область": "Tomsk",
    "Тульская область": "Tula",
    "Тюменская область": "Tyumen'",
    "Ульяновская область": "Ul'yanovsk",
    "Хабаровский край": "Khabarovsk",
    "Челябинская область": "Chelyabinsk",
    "Ярославская область": "Yaroslavl'",
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
    "Республика Крым": "Krym",
    "Республика Марий Эл": "Mariy-El",
    "Республика Мордовия": "Mordovia",
    "Республика Саха (Якутия)": "Sakha",
    "Республика Северная Осетия - Алания": "North Ossetia",
    "Республика Татарстан": "Tatarstan",
    "Республика Тыва": "Tuva",
    "Удмуртская Республика": "Udmurt",
    "Республика Хакасия": "Khakass",
    "Чеченская Республика": "Chechnya",
    "Чувашская Республика": "Chuvash",
    "Ненецкий автономный округ": "Nenets",
    "Ханты-Мансийский автономный округ - Югра": "Khanty-Mansiy",
    "Чукотский автономный округ": "Chukot",
    "Ямало-Ненецкий автономный округ": "Yamal-Nenets",
    "город Москва": "MoscowCity",
    "город Санкт-Петербург": "CityofSt.Petersburg",
    "город Севастополь": "Sevastopol'",
    # Дополнительные маппинги для вариантов названий
    "Кемеровская область - Кузбасс": "Kemerovo",
    "Республика Татарстан (Татарстан)": "Tatarstan",
    "Республика Северная Осетия - Алания": "NorthOssetia",
    "Республика Крым": "Krym",  # Может отсутствовать в GADM
    # Эти регионы отсутствуют в GADM (спорные территории)
    # "Донецкая Народная Республика": None,
    # "Луганская Народная Республика": None,
}


def import_regions(engine, gadm_data: dict, excel_df: pd.DataFrame):
    """Импортировать ВСЕ регионы из Excel в базу данных."""
    print("\n=== Импорт регионов ===")
    
    # Получаем уникальные регионы из Excel
    excel_regions = excel_df['region_name'].unique()
    print(f"Регионов в Excel: {len(excel_regions)}")
    
    # Получаем регионы из GADM
    gadm_features = gadm_data.get('features', [])
    print(f"Регионов в GADM: {len(gadm_features)}")
    
    # Создаем маппинг NAME_1 -> GADM feature
    gadm_map = {}
    for feat in gadm_features:
        props = feat.get('properties', {})
        name = props.get('NAME_1', '')
        if name:
            gadm_map[name] = feat
    
    with engine.connect() as conn:
        # Очищаем таблицу регионов
        conn.execute(text("TRUNCATE TABLE regions CASCADE"))
        conn.commit()
        print("Таблица regions очищена")
        
        imported_with_geom = 0
        imported_without_geom = 0
        used_codes = set()
        
        for region_name in excel_regions:
            # Сначала пробуем точный маппинг
            gadm_name = REGION_MAPPING.get(region_name)
            feat = gadm_map.get(gadm_name) if gadm_name else None
            
            if feat:
                geom = feat.get('geometry')
                props = feat.get('properties', {})
                code = props.get('GID_1', '')
                
                # Пропускаем если код уже использован
                if code in used_codes:
                    print(f"  ПРОПУСК (дубль кода): {region_name} -> {code}")
                    continue
                used_codes.add(code)
                
                geom_json = json.dumps(geom, ensure_ascii=False)
                
                sql = text("""
                    INSERT INTO regions (id, name, name_original, code, geom, geom_simplified, bbox, created_at, updated_at, is_active)
                    VALUES (
                        gen_random_uuid(),
                        :name,
                        :name_original,
                        :code,
                        ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326),
                        ST_Multi(
                            ST_CollectionExtract(
                                ST_SimplifyPreserveTopology(
                                    ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)),
                                    0.01
                                ),
                                3
                            )
                        ),
                        ST_Envelope(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))),
                        NOW(),
                        NOW(),
                        true
                    )
                """)
                
                conn.execute(sql, {
                    'name': region_name,
                    'name_original': props.get('NAME_1', region_name),
                    'code': code,
                    'geom': geom_json
                })
                imported_with_geom += 1
                print(f"  + {region_name} -> {props.get('NAME_1')} [с геометрией]")
            else:
                # Импортируем БЕЗ геометрии
                sql = text("""
                    INSERT INTO regions (id, name, name_original, code, created_at, updated_at, is_active)
                    VALUES (
                        gen_random_uuid(),
                        :name,
                        :name_original,
                        :code,
                        NOW(),
                        NOW(),
                        true
                    )
                """)
                
                conn.execute(sql, {
                    'name': region_name,
                    'name_original': region_name,
                    'code': f'EXCEL_{region_name[:20]}'
                })
                imported_without_geom += 1
                print(f"  + {region_name} [БЕЗ геометрии]")
        
        conn.commit()
        
    print(f"\nИмпортировано регионов: {imported_with_geom + imported_without_geom}")
    print(f"  - с геометрией: {imported_with_geom}")
    print(f"  - без геометрии: {imported_without_geom}")


def transliterate_to_latin(text: str) -> str:
    """Транслитерировать русский текст в латиницу."""
    try:
        return translit(text, 'ru', reversed=True).lower()
    except:
        return text.lower()


def normalize_district_name(name: str) -> str:
    """Нормализовать название района для сопоставления с GADM."""
    if not name:
        return ""
    
    # Убираем типичные суффиксы
    name = name.replace(" муниципальный район", "")
    name = name.replace(" городской округ", "")
    name = name.replace(" район", "")
    name = name.replace(" округ", "")
    name = name.strip()
    
    # Транслитерируем
    latin = transliterate_to_latin(name)
    
    # Убираем пробелы и дефисы
    latin = latin.replace(" ", "").replace("-", "").replace("'", "")
    
    return latin


def import_districts(engine, gadm_data: dict, excel_df: pd.DataFrame):
    """Импортировать ВСЕ районы из Excel в базу данных."""
    print("\n=== Импорт районов ===")
    
    gadm_features = gadm_data.get('features', [])
    print(f"Районов в GADM: {len(gadm_features)}")
    
    # Создаем маппинг region_code -> normalized_district_name -> GADM feature
    gadm_map = {}
    for feat in gadm_features:
        props = feat.get('properties', {})
        region_name = props.get('NAME_1', '')
        district_name = props.get('NAME_2', '')
        
        if region_name and district_name:
            if region_name not in gadm_map:
                gadm_map[region_name] = {}
            
            # Нормализуем название района GADM (убираем rayon и др.)
            norm_district = district_name.lower().replace("rayon", "").replace("gorsovet", "").replace("'", "").strip()
            gadm_map[region_name][norm_district] = feat
    
    with engine.connect() as conn:
        # Очищаем таблицу районов
        conn.execute(text("TRUNCATE TABLE districts CASCADE"))
        conn.commit()
        print("Таблица districts очищена")
        
        # Получаем ID регионов и их GADM названия
        result = conn.execute(text("SELECT id, name, name_original FROM regions"))
        region_info = {row.name: {'id': row.id, 'gadm_name': row.name_original} for row in result}
        
        imported_with_geom = 0
        imported_without_geom = 0
        
        for _, row in excel_df.iterrows():
            region_name = row['region_name']
            district_name = row['district_name']
            
            info = region_info.get(region_name)
            if not info:
                print(f"  ПРОПУСК (регион не найден): {region_name} / {district_name}")
                continue
            
            region_id = info['id']
            gadm_region = info['gadm_name']
            
            # Нормализуем название района из Excel
            norm_district = normalize_district_name(district_name)
            
            feat = None
            if gadm_region in gadm_map:
                # Ищем по нормализованному названию
                for gadm_district, f in gadm_map[gadm_region].items():
                    # Сравниваем нормализованные названия
                    if norm_district in gadm_district or gadm_district in norm_district:
                        feat = f
                        break
                    # Также сравниваем начало названий (минимум 4 символа)
                    if len(norm_district) >= 4 and gadm_district.startswith(norm_district[:4]):
                        feat = f
                        break
            
            if feat:
                geom = feat.get('geometry')
                geom_json = json.dumps(geom, ensure_ascii=False)
                
                sql = text("""
                    INSERT INTO districts (id, region_id, name, osm_id, admin_level, geom, geom_simplified, created_at)
                    VALUES (
                        gen_random_uuid(),
                        :region_id,
                        :name,
                        :osm_id,
                        :admin_level,
                        ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326),
                        ST_Multi(
                            ST_CollectionExtract(
                                ST_SimplifyPreserveTopology(
                                    ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)),
                                    0.005
                                ),
                                3
                            )
                        ),
                        NOW()
                    )
                """)
                
                conn.execute(sql, {
                    'region_id': str(region_id),
                    'name': district_name,
                    'osm_id': None,
                    'admin_level': 6,
                    'geom': geom_json
                })
                imported_with_geom += 1
            else:
                # Импортируем БЕЗ геометрии
                sql = text("""
                    INSERT INTO districts (id, region_id, name, admin_level, created_at)
                    VALUES (
                        gen_random_uuid(),
                        :region_id,
                        :name,
                        :admin_level,
                        NOW()
                    )
                """)
                
                conn.execute(sql, {
                    'region_id': str(region_id),
                    'name': district_name,
                    'admin_level': 6
                })
                imported_without_geom += 1
        
        conn.commit()
        
    print(f"Импортировано районов: {imported_with_geom + imported_without_geom}")
    print(f"  - с геометрией: {imported_with_geom}")
    print(f"  - без геометрии: {imported_without_geom}")


def create_admin_centers_table(engine):
    """Создать таблицу административных центров если её нет."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'admin_centers'
            )
        """))
        exists = result.scalar()
        
        if not exists:
            print("\nСоздаём таблицу admin_centers...")
            conn.execute(text("""
                CREATE TABLE admin_centers (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    district_id UUID REFERENCES districts(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    population INTEGER,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                );
                SELECT AddGeometryColumn('admin_centers', 'geom', 4326, 'POINT', 2);
                CREATE INDEX idx_admin_centers_district_id ON admin_centers(district_id);
                CREATE INDEX idx_admin_centers_geom ON admin_centers USING GIST(geom);
            """))
            conn.commit()
            print("Таблица admin_centers создана")


def import_admin_centers(engine, excel_df: pd.DataFrame):
    """Импортировать ВСЕ административные центры из Excel."""
    print("\n=== Импорт административных центров ===")
    
    with engine.connect() as conn:
        # Очищаем таблицу
        conn.execute(text("TRUNCATE TABLE admin_centers CASCADE"))
        conn.commit()
        
        # Получаем ID районов и информацию о геометрии
        result = conn.execute(text("""
            SELECT d.id, d.name as district_name, r.name as region_name,
                   CASE WHEN d.geom IS NOT NULL THEN true ELSE false END as has_geom
            FROM districts d 
            JOIN regions r ON d.region_id = r.id
        """))
        district_info = {(row.region_name, row.district_name): {'id': row.id, 'has_geom': row.has_geom} for row in result}
        
        imported_with_geom = 0
        imported_without_geom = 0
        
        for _, row in excel_df.iterrows():
            key = (row['region_name'], row['district_name'])
            info = district_info.get(key)
            
            if info and row['admin_center']:
                district_id = info['id']
                
                if info['has_geom']:
                    # Используем центроид района как координату центра
                    sql = text("""
                        INSERT INTO admin_centers (id, district_id, name, geom, created_at)
                        SELECT 
                            gen_random_uuid(),
                            :district_id,
                            :name,
                            ST_Centroid(d.geom),
                            NOW()
                        FROM districts d WHERE d.id = :district_id
                    """)
                    conn.execute(sql, {
                        'district_id': str(district_id),
                        'name': row['admin_center']
                    })
                    imported_with_geom += 1
                else:
                    # Без геометрии
                    sql = text("""
                        INSERT INTO admin_centers (id, district_id, name, created_at)
                        VALUES (gen_random_uuid(), :district_id, :name, NOW())
                    """)
                    conn.execute(sql, {
                        'district_id': str(district_id),
                        'name': row['admin_center']
                    })
                    imported_without_geom += 1
        
        conn.commit()
        
    print(f"Импортировано административных центров: {imported_with_geom + imported_without_geom}")
    print(f"  - с геометрией: {imported_with_geom}")
    print(f"  - без геометрии: {imported_without_geom}")


def main():
    excel_path = r"C:\Users\Lucky\Downloads\123.xlsx"
    
    print("=" * 60)
    print("ИМПОРТ АДМИНИСТРАТИВНЫХ ДАННЫХ РФ")
    print("=" * 60)
    
    # Подключаемся к БД
    engine = create_engine(settings.DATABASE_URL)
    print(f"\nПодключение к БД: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'OK'}")
    
    # Загружаем Excel
    print("\n1. Загрузка данных из Excel...")
    excel_df = load_excel_data(excel_path)
    print(f"   Загружено строк: {len(excel_df)}")
    print(f"   Уникальных регионов: {excel_df['region_name'].nunique()}")
    print(f"   Уникальных районов: {excel_df['district_name'].nunique()}")
    
    # Скачиваем GADM данные
    print("\n2. Скачивание геометрии регионов (GADM level 1)...")
    gadm_regions = download_gadm_data(1)
    
    print("\n3. Скачивание геометрии районов (GADM level 2)...")
    gadm_districts = download_gadm_data(2)
    
    # Импортируем
    print("\n4. Импорт данных в базу...")
    import_regions(engine, gadm_regions, excel_df)
    import_districts(engine, gadm_districts, excel_df)
    
    # Создаем и заполняем таблицу админ центров
    create_admin_centers_table(engine)
    import_admin_centers(engine, excel_df)
    
    print("\n" + "=" * 60)
    print("ИМПОРТ ЗАВЕРШЁН!")
    print("=" * 60)


if __name__ == "__main__":
    main()
