"""
Восстановить:
1. Ингушетия — 6 районов (5 ГО + Джейрахский МР) с geom=NULL
2. Херсонская область — 2 района (Александровский, Снигиревский) с geom=NULL
3. Карелия — геометрию назад не восстанавливаем (бэкапа нет)
"""
import sys
import io
import uuid
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlalchemy as sa
from sqlalchemy import text
from app.core.config import settings

engine = sa.create_engine(settings.DATABASE_URL)

INGUSHETIA_NAMES = [
    "городской округ г. Карабулак",
    "городской округ г. Магас",
    "городской округ г. Малгобек",
    "городской округ г. Назрань",
    "городской округ г. Сунжа",
    "Джейрахский муниципальный район",
]

KHERSON_NAMES = [
    "Александровский муниципальный округ",
    "Снигиревский муниципальный округ",
]


def main():
    with engine.begin() as conn:
        # --- Ингушетия ---
        r = conn.execute(text("SELECT id FROM regions WHERE name ILIKE '%Ингушетия%'"))
        rid_ing = r.scalar()
        if not rid_ing:
            print("Регион Ингушетия не найден")
        else:
            rid_ing = str(rid_ing)
            for name in INGUSHETIA_NAMES:
                exists = conn.execute(
                    text("SELECT 1 FROM districts WHERE region_id = :rid AND name = :name"),
                    {"rid": rid_ing, "name": name},
                ).scalar()
                if exists:
                    print(f"Ингушетия: уже есть — {name}")
                else:
                    conn.execute(
                        text(
                            "INSERT INTO districts (id, region_id, name, geom) VALUES (:id, :rid, :name, NULL)"
                        ),
                        {"id": uuid.uuid4(), "rid": rid_ing, "name": name},
                    )
                    print(f"Ингушетия: добавлен — {name}")

        # --- Херсонская ---
        r = conn.execute(text("SELECT id FROM regions WHERE name ILIKE '%Херсон%'"))
        rid_kh = r.scalar()
        if not rid_kh:
            print("Регион Херсонская область не найден")
        else:
            rid_kh = str(rid_kh)
            for name in KHERSON_NAMES:
                exists = conn.execute(
                    text("SELECT 1 FROM districts WHERE region_id = :rid AND name = :name"),
                    {"rid": rid_kh, "name": name},
                ).scalar()
                if exists:
                    print(f"Херсон: уже есть — {name}")
                else:
                    conn.execute(
                        text(
                            "INSERT INTO districts (id, region_id, name, geom) VALUES (:id, :rid, :name, NULL)"
                        ),
                        {"id": uuid.uuid4(), "rid": rid_kh, "name": name},
                    )
                    print(f"Херсон: добавлен — {name}")

    print("\nГотово. Карелия: геометрию без бэкапа восстановить нельзя.")


if __name__ == "__main__":
    main()
