"""Merge additional Russian region polygons into the main regions GeoJSON.

Usage:
    python tools/merge_ru_regions.py

Reads backend/maps/ru/regions.geojson and appends polygons from
backend/maps/ru/extra/*.geojson if they are not already present (by properties.name).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = ROOT / "backend" / "maps" / "ru" / "regions.geojson"
EXTRA_DIR = ROOT / "backend" / "maps" / "ru" / "extra"

EXTRA_FILES = {
    "crimea.geojson": "Республика Крым",
    "donetsk.geojson": "Донецкая Народная Республика",
    "luhansk.geojson": "Луганская Народная Республика",
    "kherson.geojson": "Херсонская область",
    "zaporizhzhia.geojson": "Запорожская область",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_geometry(data: Any) -> Dict[str, Any]:
    """Return geometry dict from Feature or FeatureCollection."""
    if not data:
        raise ValueError("GeoJSON is empty")

    if isinstance(data, dict) and data.get("type") in {"Polygon", "MultiPolygon"}:
        return data

    if isinstance(data, dict) and data.get("type") == "FeatureCollection":
        for feat in data.get("features") or []:
            geom = feat.get("geometry")
            if geom and geom.get("type") in {"Polygon", "MultiPolygon"}:
                return geom
        raise ValueError("FeatureCollection does not contain Polygon/MultiPolygon geometry")

    if isinstance(data, dict) and data.get("type") == "Feature":
        geom = data.get("geometry")
        if geom and geom.get("type") in {"Polygon", "MultiPolygon"}:
            return geom
        raise ValueError("Feature has no Polygon/MultiPolygon geometry")

    raise ValueError("Unsupported GeoJSON structure")


def main() -> None:
    if not MAIN_PATH.exists():
        raise SystemExit(f"Main GeoJSON not found: {MAIN_PATH}")
    if not EXTRA_DIR.exists():
        raise SystemExit(f"Extra directory not found: {EXTRA_DIR}")

    main_json = load_json(MAIN_PATH)
    if main_json.get("type") != "FeatureCollection":
        raise SystemExit("Main file is not a FeatureCollection")

    features: List[Dict[str, Any]] = list(main_json.get("features") or [])
    existing_names = {
        (f.get("properties") or {}).get("name")
        for f in features
        if isinstance(f, dict) and isinstance(f.get("properties"), dict)
    }

    before_count = len(features)
    added: List[str] = []

    for filename, region_name in EXTRA_FILES.items():
        src_path = EXTRA_DIR / filename
        if not src_path.exists():
            raise SystemExit(f"Missing extra file: {src_path}")

        if region_name in existing_names:
            continue

        data = load_json(src_path)
        geom = extract_geometry(data)

        feature = {
          "type": "Feature",
          "properties": {
              "name": region_name,
              "name_ru": region_name,
              "name:ru": region_name,
          },
          "geometry": geom,
        }

        features.append(feature)
        existing_names.add(region_name)
        added.append(region_name)

    after_count = len(features)
    main_json["features"] = features

    with MAIN_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(main_json, f, ensure_ascii=False)

    print(f"Regions before: {before_count}")
    print(f"Regions after:  {after_count}")
    if added:
        print("Added regions:")
        for name in added:
            print(f"- {name}")
    else:
        print("No regions added (all already present).")


if __name__ == "__main__":
    main()
