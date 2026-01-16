#!/usr/bin/env python
"""Извлечение всех названий регионов из GeoJSON для создания маппинга."""
import json
from pathlib import Path

GEOJSON_PATH = Path(__file__).parent.parent / "maps" / "ru" / "regions.geojson"


def get_name(props: dict) -> str:
    """Извлекает имя региона из свойств GeoJSON."""
    for key in ("name", "name_ru", "NAME", "NAME_1"):
        if key in props and props[key]:
            return str(props[key]).strip()
    return ""


def main():
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        fc = json.load(f)

    names = []
    for feature in fc.get("features", []):
        name = get_name(feature.get("properties") or {})
        if name:
            names.append(name)
    
    print("Все названия из GeoJSON (name_original):")
    for name in sorted(names):
        print(f'  "{name}",')
    
    print(f"\nВсего регионов: {len(names)}")


if __name__ == "__main__":
    main()
