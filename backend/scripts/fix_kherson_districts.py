"""
Привести Херсонскую область к заданному перечню районов/округов.
Добавить недостающие, переименовать «район» -> «муниципальный округ» где нужно, удалить лишние.
"""
import os
import sys
import json
import uuid

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

REGION_NAME = "Херсонская область"

# Целевой список (единственный источник истины)
TARGET_NAMES = [
    "городской округ Херсон",
    "городской округ Новая Каховка",
    "Александровский муниципальный округ",
    "Алешкинский муниципальный округ",
    "Белозерский муниципальный округ",
    "Бериславский муниципальный округ",
    "Великоалександровский муниципальный округ",
    "Великолепетихский муниципальный округ",
    "Верхнерогачикский муниципальный округ",
    "Высокопольский муниципальный округ",
    "Генический муниципальный округ",
    "Голопристанский муниципальный округ",
    "Горностаевский муниципальный округ",
    "Ивановский муниципальный округ",
    "Каланчакский муниципальный округ",
    "Каховский муниципальный округ",
    "Нижнесерогозский муниципальный округ",
    "Нововоронцовский муниципальный округ",
    "Новотроицкий муниципальный округ",
    "Скадовский муниципальный округ",
    "Снигиревский муниципальный округ",
    "Чаплинский муниципальный округ",
]

# Возможные старые названия -> целевое (для переименования без удаления)
OLD_TO_TARGET = {
    "город Херсон": "городской округ Херсон",
    "городской округ город Херсон": "городской округ Херсон",
    "город Новая Каховка": "городской округ Новая Каховка",
    "городской округ город Новая Каховка": "городской округ Новая Каховка",
}
for name in TARGET_NAMES:
    if "муниципальный округ" in name:
        base = name.replace(" муниципальный округ", "")
        OLD_TO_TARGET[base + " муниципальный район"] = name
# Варианты написания
OLD_TO_TARGET["Нижнесирогозский муниципальный район"] = "Нижнесерогозский муниципальный округ"
OLD_TO_TARGET["Нижнесирогозский муниципальный округ"] = "Нижнесерогозский муниципальный округ"


def main():
    target_set = set(TARGET_NAMES)
    print(f"Приведение «{REGION_NAME}» к перечню из {len(TARGET_NAMES)} записей")
    print("=" * 60)

    with engine.begin() as conn:
        region_id = conn.execute(
            text("SELECT id FROM regions WHERE name = :name"),
            {"name": REGION_NAME},
        ).scalar()
        if not region_id:
            print(f"Регион «{REGION_NAME}» не найден.")
            return

        # Текущие районы
        rows = conn.execute(
            text("""
                SELECT d.id, d.name FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region
            """),
            {"region": REGION_NAME},
        ).fetchall()
        current = {r[1]: r[0] for r in rows}

        # 1) Переименовать: если текущее не в target_set, но есть в OLD_TO_TARGET -> переименовать
        for old_name, new_name in OLD_TO_TARGET.items():
            if old_name not in current or new_name in current:
                continue
            did = current[old_name]
            conn.execute(
                text("UPDATE districts SET name = :new WHERE id = :id"),
                {"new": new_name, "id": did},
            )
            conn.execute(
                text("UPDATE events SET district_name = :new WHERE district_name = :old"),
                {"new": new_name, "old": old_name},
            )
            # Зоны
            for row in conn.execute(text("SELECT id, district_names FROM administrative_zones")).fetchall():
                zone_id, dn = row[0], row[1]
                if not dn:
                    continue
                try:
                    arr = dn if isinstance(dn, list) else json.loads(dn)
                except Exception:
                    continue
                new_arr = []
                seen = set()
                for x in arr:
                    s = str(x).strip()
                    if s == old_name:
                        s = new_name
                    if s and s not in seen:
                        seen.add(s)
                        new_arr.append(s)
                if old_name in arr:
                    conn.execute(
                        text("UPDATE administrative_zones SET district_names = :dj WHERE id = :id"),
                        {"dj": json.dumps(new_arr, ensure_ascii=False), "id": zone_id},
                    )
            print(f"  Переименован: «{old_name}» → «{new_name}»")
            current[new_name] = did
            del current[old_name]

        # 2) Удалить все, чего нет в target_set
        to_delete = [name for name in current if name not in target_set]
        for name in to_delete:
            conn.execute(
                text("""
                    DELETE FROM districts d
                    USING regions r
                    WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
                """),
                {"region": REGION_NAME, "name": name},
            )
            print(f"  Удалён: «{name}»")

        # 3) Добавить недостающие (после удалений перечитываем список)
        existing_names = set(
            row[0] for row in conn.execute(
                text("""
                    SELECT d.name FROM districts d
                    JOIN regions r ON d.region_id = r.id
                    WHERE r.name = :region
                """),
                {"region": REGION_NAME},
            ).fetchall()
        )
        for name in TARGET_NAMES:
            if name in existing_names:
                continue
            conn.execute(
                text("INSERT INTO districts (id, region_id, name, geom) VALUES (:id, :rid, :name, NULL)"),
                {"id": uuid.uuid4(), "rid": region_id, "name": name},
            )
            print(f"  Добавлен: «{name}»")

    print("\nГотово. Текущий перечень:")
    with engine.connect() as c:
        rows = c.execute(
            text("""
                SELECT d.name FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region
                ORDER BY d.name
            """),
            {"region": REGION_NAME},
        ).fetchall()
        for r in rows:
            print(f"  - {r[0]}")


if __name__ == "__main__":
    main()
