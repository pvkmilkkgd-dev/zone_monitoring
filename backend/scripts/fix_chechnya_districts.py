"""
Привести Чеченскую Республику к заданному перечню районов/округов.
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

REGION_NAME = "Чеченская Республика"

TARGET_NAMES = [
    "городской округ город Грозный",
    "городской округ город Аргун",
    "Ачхой-Мартановский муниципальный район",
    "Веденский муниципальный район",
    "Грозненский муниципальный район",
    "Гудермесский муниципальный район",
    "Итум-Калинский муниципальный район",
    "Курчалоевский муниципальный район",
    "Надтеречный муниципальный район",
    "Наурский муниципальный район",
    "Ножай-Юртовский муниципальный район",
    "Серноводский муниципальный район",
    "Урус-Мартановский муниципальный район",
    "Шалинский муниципальный район",
    "Шаройский муниципальный район",
    "Шатойский муниципальный район",
    "Шелковской муниципальный район",
]

# Старые названия -> целевое (район/округ, город/ГО)
OLD_TO_TARGET = {
    "город Грозный": "городской округ город Грозный",
    "городской округ Грозный": "городской округ город Грозный",
    "город Аргун": "городской округ город Аргун",
    "городской округ Аргун": "городской округ город Аргун",
}
for name in TARGET_NAMES:
    if "муниципальный район" in name:
        base = name.replace(" муниципальный район", "")
        OLD_TO_TARGET[base + " муниципальный округ"] = name


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

        rows = conn.execute(
            text("""
                SELECT d.id, d.name FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region
            """),
            {"region": REGION_NAME},
        ).fetchall()
        current = {r[1]: r[0] for r in rows}

        # 1) Переименовать по маппингу
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
                        s = new_name
                    if s and s not in seen:
                        seen.add(s)
                        new_arr.append(s)
                conn.execute(
                    text("UPDATE administrative_zones SET district_names = :dj WHERE id = :id"),
                    {"dj": json.dumps(new_arr, ensure_ascii=False), "id": zone_id},
                )
            print(f"  Переименован: «{old_name}» → «{new_name}»")
            current[new_name] = did
            del current[old_name]

        # 2) Удалить всё, чего нет в target_set
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

        # 3) Добавить недостающие
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
        for r in c.execute(
            text("""
                SELECT d.name FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region
                ORDER BY d.name
            """),
            {"region": REGION_NAME},
        ).fetchall():
            print(f"  - {r[0]}")


if __name__ == "__main__":
    main()
