#!/usr/bin/env python
"""Скачивание GeoJSON файла для Сумской области из различных источников."""
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: Установите библиотеку requests: pip install requests")
    sys.exit(1)

# Путь к файлу
GEOJSON_PATH = Path(__file__).parent.parent / "maps" / "ru" / "extra" / "sumy.geojson"


def download_from_osm_relation():
    """Скачивание данных из OpenStreetMap через Overpass API."""
    print("Попытка скачать из OpenStreetMap (Overpass API)...")
    
    # Запрос для получения границ Сумской области
    query = """[out:json][timeout:25];
relation["name"~"Сумська|Сумская|Sumy"]["admin_level"="4"]["type"="boundary"];
out geom;
"""
    
    try:
        response = requests.post(
            "https://overpass-api.de/api/interpreter",
            data=query,
            headers={"Content-Type": "text/plain"},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("elements") and len(data["elements"]) > 0:
            element = data["elements"][0]
            tags = element.get("tags", {})
            name = tags.get("name:ru") or tags.get("name") or "Сумская область"
            
            # Получаем координаты из members
            members = element.get("members", [])
            all_coords = []
            
            for member in members:
                if member.get("type") == "way" and member.get("geometry"):
                    way_coords = [[float(p["lon"]), float(p["lat"])] for p in member["geometry"]]
                    all_coords.extend(way_coords)
            
            if all_coords:
                # Замыкаем полигон
                if all_coords[0] != all_coords[-1]:
                    all_coords.append(all_coords[0])
                
                geojson = {
                    "type": "FeatureCollection",
                    "features": [{
                        "type": "Feature",
                        "properties": {"name": name},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [all_coords]
                        }
                    }]
                }
                
                with open(GEOJSON_PATH, "w", encoding="utf-8") as f:
                    json.dump(geojson, f, ensure_ascii=False, indent=2)
                
                print(f"OK Скачано из OSM: {len(all_coords)} точек")
                return True
    except Exception as e:
        print(f"  Ошибка OSM: {e}")
    
    return False


def download_from_gadm():
    """Попытка скачать из GADM."""
    print("Попытка скачать из GADM...")
    # GADM требует регистрации, поэтому пропускаем
    return False


def download_from_github_sources():
    """Попытка скачать из различных GitHub источников."""
    sources = [
        "https://raw.githubusercontent.com/EugeneBorshch/ukraine_geojson/master/sumy.geojson",
        "https://raw.githubusercontent.com/isellsoap/ukraineGeoJSON/master/geojson/ua_oblast_sumy.geojson",
    ]
    
    for url in sources:
        try:
            print(f"  Попытка: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Проверяем, что это валидный GeoJSON
            if data.get("type") == "FeatureCollection" and data.get("features"):
                # Убеждаемся, что имя правильное
                for feature in data["features"]:
                    props = feature.get("properties", {})
                    if "name" in props:
                        props["name"] = "Сумская область"
                
                with open(GEOJSON_PATH, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                print(f"OK Скачано из GitHub: {url}")
                return True
        except Exception as e:
            print(f"  Ошибка: {e}")
            continue
    
    return False


def main():
    print("=== Скачивание GeoJSON для Сумской области ===\n")
    
    # Пробуем различные источники
    if download_from_osm_relation():
        return
    
    if download_from_github_sources():
        return
    
    print("\nFAIL Не удалось скачать из известных источников.")
    print("  Пожалуйста, вручную скачайте GeoJSON файл с границами Сумской области")
    print("  и сохраните его как:", GEOJSON_PATH)
    print("\n  Рекомендуемые источники:")
    print("    - https://github.com/EugeneBorshch/ukraine_geojson")
    print("    - https://gadm.org/download_country.html")
    print("    - https://geo2day.com/europe/ukraine/sumy_oblast.html")


if __name__ == "__main__":
    main()
