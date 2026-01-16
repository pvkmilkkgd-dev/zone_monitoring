#!/usr/bin/env python
"""Скачивание официального GeoJSON для Сумской области."""
import json
import sys
from pathlib import Path

try:
    import requests
    from io import BytesIO
    import zipfile
except ImportError:
    print("ERROR: Установите библиотеку requests: pip install requests")
    sys.exit(1)

GEOJSON_PATH = Path(__file__).parent.parent / "maps" / "ru" / "extra" / "sumy.geojson"


def download_from_gadm():
    """Скачивание из GADM (Global Administrative Areas)."""
    print("Попытка скачать из GADM...")
    
    # GADM предоставляет данные по Украине, но нужно извлечь конкретную область
    # Попробуем прямой URL для уровня 1 (области)
    try:
        # GADM предоставляет Shapefile, но мы можем использовать готовый GeoJSON
        # Попробуем найти готовый GeoJSON для Sumy Oblast (UA-59)
        url = "https://gadm.org/download_country_json.html"
        print("  GADM требует ручной выбор. Пробуем альтернативные источники...")
        return False
    except Exception as e:
        print(f"  Ошибка GADM: {e}")
        return False


def download_from_simplemaps():
    """Попытка скачать из SimpleMaps."""
    print("Попытка скачать из SimpleMaps...")
    
    try:
        # SimpleMaps предоставляет данные по областям Украины
        url = "https://simplemaps.com/static/data/country-json/ua.json"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # Ищем Сумскую область (UA-59 или Sumy)
        if isinstance(data, dict) and "features" in data:
            for feature in data["features"]:
                props = feature.get("properties", {})
                name = props.get("name", "").lower()
                code = props.get("iso", "") or props.get("code", "")
                
                # Проверяем различные варианты названия
                if "sumy" in name or "sumsk" in name or code == "UA-59" or "UA59" in str(code):
                    # Нашли Сумскую область
                    feature["properties"]["name"] = "Сумская область"
                    
                    geojson = {
                        "type": "FeatureCollection",
                        "features": [feature]
                    }
                    
                    with open(GEOJSON_PATH, "w", encoding="utf-8") as f:
                        json.dump(geojson, f, ensure_ascii=False, indent=2)
                    
                    print(f"OK Скачано из SimpleMaps")
                    return True
        
        print("  Сумская область не найдена в данных SimpleMaps")
        return False
    except Exception as e:
        print(f"  Ошибка SimpleMaps: {e}")
        return False


def download_from_osm_nominatim():
    """Использование Nominatim для получения данных из OSM."""
    print("Попытка использовать Nominatim (OpenStreetMap)...")
    
    try:
        # Ищем relation для Сумской области через Nominatim
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": "Sumy Oblast Ukraine",
            "format": "json",
            "limit": 1,
            "polygon_geojson": 1,
            "addressdetails": 1
        }
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if data and len(data) > 0:
            item = data[0]
            if "geojson" in item:
                geojson_data = item["geojson"]
                
                # Преобразуем в правильный формат
                geojson = {
                    "type": "FeatureCollection",
                    "features": [{
                        "type": "Feature",
                        "properties": {
                            "name": "Сумская область"
                        },
                        "geometry": geojson_data
                    }]
                }
                
                with open(GEOJSON_PATH, "w", encoding="utf-8") as f:
                    json.dump(geojson, f, ensure_ascii=False, indent=2)
                
                print(f"OK Скачано из Nominatim/OSM")
                return True
        
        print("  Данные не найдены в Nominatim")
        return False
    except Exception as e:
        print(f"  Ошибка Nominatim: {e}")
        return False


def download_from_github_official():
    """Попытка скачать из официальных GitHub репозиториев."""
    print("Попытка скачать из GitHub...")
    
    sources = [
        # Попробуем найти репозитории с данными Украины
        "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/ukraine.geojson",
        "https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/world.geojson",
    ]
    
    for url in sources:
        try:
            print(f"  Попытка: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Ищем Сумскую область
            if data.get("type") == "FeatureCollection":
                for feature in data.get("features", []):
                    props = feature.get("properties", {})
                    name = str(props.get("name", "")).lower()
                    
                    if "sumy" in name or "сумск" in name or "UA-59" in str(props.get("code", "")):
                        feature["properties"]["name"] = "Сумская область"
                        
                        geojson = {
                            "type": "FeatureCollection",
                            "features": [feature]
                        }
                        
                        with open(GEOJSON_PATH, "w", encoding="utf-8") as f:
                            json.dump(geojson, f, ensure_ascii=False, indent=2)
                        
                        print(f"OK Скачано из GitHub: {url}")
                        return True
        
        except Exception as e:
            print(f"  Ошибка {url}: {e}")
            continue
    
    return False


def main():
    print("=== Скачивание официального GeoJSON для Сумской области ===\n")
    
    # Пробуем различные официальные источники
    if download_from_simplemaps():
        return
    
    if download_from_osm_nominatim():
        return
    
    if download_from_github_official():
        return
    
    print("\nFAIL Не удалось скачать из официальных источников.")
    print("  Рекомендуется:")
    print("    1. Скачать вручную с https://gadm.org/download_country.html (выбрать Ukraine, GeoJSON)")
    print("    2. Использовать данные с https://github.com/EugeneBorshch/ukraine_geojson")
    print("    3. Или использовать созданный ранее файл с реалистичными координатами")


if __name__ == "__main__":
    main()
