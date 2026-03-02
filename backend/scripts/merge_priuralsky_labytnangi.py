"""
Объединить геометрии Приуральский район и город Лабытнанги (ЯНАО)
в одну запись «Муниципальный округ Приуральский район».
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
except ImportError:
    pass

import sqlalchemy as sa
from sqlalchemy import text

db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/zone_monitoring")
if db_url.startswith("postgresql+psycopg"):
    db_url = db_url.replace("postgresql+psycopg", "postgresql", 1)
engine = sa.create_engine(db_url)

REGION_NAME = "Ямало-Ненецкий автономный округ"
KEEP_NAME = "Муниципальный округ Приуральский район"
# Варианты названий для объединения (район и город)
NAMES_TO_MERGE = [
    "Муниципальный округ Приуральский район",
    "Приуральский район",
    "город Лабытнанги",
]


def main():
    print(f"Объединение Приуральский + Лабытнанги в «{REGION_NAME}»")
    print("=" * 60)
    print(f"Итоговое название: «{KEEP_NAME}»")
    print("=" * 60)

    with engine.begin() as conn:
        # Найти все подходящие районы в регионе
        rows = conn.execute(
            text("""
                SELECT d.id, d.name, d.geom IS NOT NULL as has_geom
                FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region
                  AND (d.name LIKE '%Приуральск%' OR d.name LIKE '%Лабытнанги%')
            """),
            {"region": REGION_NAME},
        ).fetchall()

        if not rows:
            print("\n✗ Не найдено записей Приуральский / Лабытнанги в регионе.")
            return

        for r in rows:
            print(f"  Найден: «{r[1]}» (id={r[0]}, геометрия={'есть' if r[2] else 'нет'})")

        # Выбираем запись, которую оставим: предпочтительно уже с именем KEEP_NAME
        keeper = None
        others = []
        for r in rows:
            if r[1] == KEEP_NAME:
                keeper = r
            else:
                others.append(r)

        if not keeper:
            keeper = rows[0]
            others = rows[1:]
            # Переименуем в KEEP_NAME
            conn.execute(
                text("UPDATE districts SET name = :name WHERE id = :id"),
                {"name": KEEP_NAME, "id": keeper[0]},
            )
            print(f"\n  Переименован в «{KEEP_NAME}»: id={keeper[0]}")

        keeper_id = keeper[0]
        # Собираем все геометрии для объединения (keeper + others с geom)
        ids_with_geom = [keeper_id]
        for r in others:
            if r[2]:
                ids_with_geom.append(r[0])

        if len(ids_with_geom) >= 2:
            # ST_Union всех geom по id
            conn.execute(
                text("""
                    UPDATE districts
                    SET geom = (
                        SELECT ST_Multi(ST_MakeValid(ST_Union(geom)))
                        FROM districts
                        WHERE id = ANY(:ids) AND geom IS NOT NULL
                    )
                    WHERE id = :keeper_id
                """),
                {"ids": ids_with_geom, "keeper_id": keeper_id},
            )
            print(f"\n✓ Геометрии объединены (ST_Union по {len(ids_with_geom)} записям)")
        elif len(ids_with_geom) == 1 and keeper[2]:
            print("\n✓ Геометрия только у одной записи, оставляем как есть")
        else:
            # Копируем geom из любой другой, если у keeper нет
            for r in others:
                if r[2]:
                    conn.execute(
                        text("UPDATE districts SET geom = (SELECT geom FROM districts WHERE id = :src) WHERE id = :dst"),
                        {"src": r[0], "dst": keeper_id},
                    )
                    print(f"\n✓ Геометрия скопирована из «{r[1]}»")
                    break

        # События и зоны: старые названия -> KEEP_NAME
        for r in others:
            old_name = r[1]
            conn.execute(
                text("UPDATE events SET district_name = :new WHERE district_name = :old"),
                {"new": KEEP_NAME, "old": old_name},
            )
            for row in conn.execute(text("SELECT id, district_names FROM administrative_zones")).fetchall():
                zone_id, dn = row[0], row[1]
                if not dn:
                    continue
                try:
                    arr = dn if isinstance(dn, list) else json.loads(dn)
                except Exception:
                    continue
                if old_name not in arr:
                    continue
                new_arr = []
                seen = set()
                for x in arr:
                    s = str(x).strip()
                    if s == old_name:
                        s = KEEP_NAME
                    if s and s not in seen:
                        seen.add(s)
                        new_arr.append(s)
                conn.execute(
                    text("UPDATE administrative_zones SET district_names = :dj WHERE id = :id"),
                    {"dj": json.dumps(new_arr, ensure_ascii=False), "id": zone_id},
                )

        # Удаляем остальные записи (не keeper)
        for r in others:
            conn.execute(text("DELETE FROM districts WHERE id = :id"), {"id": r[0]})
            print(f"  Удалён: «{r[1]}»")

        # Итог
        result = conn.execute(
            text("""
                SELECT ROUND(ST_Area(d.geom::geography)/1000000), ST_NPoints(d.geom)
                FROM districts d
                WHERE d.id = :id AND d.geom IS NOT NULL
            """),
            {"id": keeper_id},
        ).fetchone()
        if result:
            print(f"\n✓ Итоговая геометрия «{KEEP_NAME}»: ~{int(result[0])} км², {result[1]} точек")

    print("\nГотово.")


if __name__ == "__main__":
    main()
