#!/usr/bin/env python
"""Скачивание GeoJSON для Сумской области через Overpass API."""
import json
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: Установите библиотеку requests: pip install requests")
    sys.exit(1)

GEOJSON_PATH = Path(__file__).parent.parent / "maps" / "ru" / "extra" / "sumy.geojson"


def download_from_overpass():
    """Скачивание через Overpass API."""
    print("Попытка скачать из Overpass API (OpenStreetMap)...")
    
    # Overpass запрос для поиска Сумской области
    query = """[out:json][timeout:30];
relation["name:en"="Sumy Oblast"]["admin_level"="4"]["type"="boundary"];
out geom;
"""
    
    try:
        servers = [
            "https://overpass-api.de/api/interpreter",
        ]
        
        for server in servers:
            try:
                print(f"  Попытка через {server}...")
                response = requests.post(
                    server,
                    data=query,
                    headers={
                        "Content-Type": "text/plain",
                        "User-Agent": "GeoJSON-downloader/1.0"
                    },
                    timeout=40
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("elements") and len(data["elements"]) > 0:
                    element = data["elements"][0]
                    tags = element.get("tags", {})
                    name = tags.get("name:ru") or tags.get("name") or "Сумская область"
                    
                    # Получаем координаты из members (ways)
                    members = element.get("members", [])
                    all_coords = []
                    
                    ways = [m for m in members if m.get("type") == "way" and m.get("geometry")]
                    
                    for way in ways:
                        geometry = way.get("geometry", [])
                        way_coords = [[float(p["lon"]), float(p["lat"])] for p in geometry]
                        all_coords.extend(way_coords)
                    
                    if all_coords and len(all_coords) > 10:
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
                        
                        print(f"OK Скачано из Overpass: {len(all_coords)} точек")
                        return True
                
                print(f"  Данные не найдены")
                
            except Exception as e:
                print(f"  Ошибка: {e}")
        
        return False
        
    except Exception as e:
        print(f"  Общая ошибка Overpass: {e}")
        return False


def main():
    print("=== Скачивание GeoJSON для Сумской области ===\n")
    
    if download_from_overpass():
        print("\nУспешно скачано!")
        return
    
    print("\nНе удалось скачать автоматически.")
    print("Текущий файл с реалистичными координатами сохранен.")


if __name__ == "__main__":
    main()
