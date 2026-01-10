import json
import os
import sys
import psycopg2

GEOJSON_PATH = os.path.join("backend", "maps", "ru", "regions.geojson")

# Пример: postgres://postgres:postgres@localhost:5432/zone_monitoring
DSN = os.environ.get("DATABASE_URL")

if not DSN:
    print("ERROR: set DATABASE_URL, e.g. postgres://user:pass@localhost:5432/dbname")
    sys.exit(1)

def get_name(props: dict) -> str:
    for k in ("name_ru", "name", "NAME", "region", "subject", "NAME_1"):
        v = props.get(k)
        if v and str(v).strip():
            return str(v).strip()
    return ""

def main():
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        fc = json.load(f)

    feats = fc.get("features", [])
    print("features:", len(feats))

    conn = psycopg2.connect(DSN)
    conn.autocommit = False

    sql = """
    INSERT INTO regions (name, geom, geom_simplified, bbox)
    VALUES (
      %(name)s,
      -- основная геометрия
      ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(%(geom)s), 4326)), 3)),
      -- упрощённая (толеранс подберём потом, но стартово норм)
      ST_Multi(
        ST_CollectionExtract(
          ST_SimplifyPreserveTopology(
            ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(%(geom)s), 4326)),
            0.05
          ),
          3
        )
      ),
      ST_Envelope(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(%(geom)s), 4326)))
    )
    ON CONFLICT (name) DO UPDATE
      SET geom = EXCLUDED.geom,
          geom_simplified = EXCLUDED.geom_simplified,
          bbox = EXCLUDED.bbox,
          updated_at = now();
    """

    cur = conn.cursor()
    ok = 0
    skipped = 0

    for f in feats:
        props = f.get("properties") or {}
        name = get_name(props)
        geom = f.get("geometry")
        if not name or not geom:
            skipped += 1
            continue

        cur.execute(sql, {"name": name, "geom": json.dumps(geom, ensure_ascii=False)})
        ok += 1

    conn.commit()
    cur.close()
    conn.close()

    print("imported:", ok, "skipped:", skipped)

if __name__ == "__main__":
    main()
