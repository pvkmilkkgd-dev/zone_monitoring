"""Проверка районов Республики Коми и Республики Карелия (Калевальский в Карелии)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
except ImportError:
    pass
db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/zone_monitoring")
if db_url.startswith("postgresql+psycopg"):
    db_url = db_url.replace("postgresql+psycopg", "postgresql", 1)
from sqlalchemy import create_engine, text

engine = create_engine(db_url)
with engine.connect() as c:
    for region in ["Республика Коми", "Республика Карелия"]:
        r = c.execute(
            text(
                "SELECT d.name FROM districts d JOIN regions r ON d.region_id = r.id WHERE r.name = :reg ORDER BY d.name"
            ),
            {"reg": region},
        )
        names = [row[0] for row in r]
        print(f"{region}: {len(names)} районов/округов")
        for n in names:
            print(f"  {n}")
        has_kalevala = any("Калевальск" in n for n in names)
        print(f"  -> Калевальский есть: {has_kalevala}")
        print()
