"""
Привести районы ДНР к полному списку ОКТМО: 18 МО + 12 ГО.
Переименовать существующие записи по соответствию, удалить лишние, добавить недостающие (без геометрии).
"""
import sys
import uuid
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)

# Полный список по ОКТМО (как прислал пользователь)
MO_LIST = [
    "Александровский муниципальный округ",
    "Амвросиевский муниципальный округ",
    "Артемовский муниципальный округ",
    "Великоновоселковский муниципальный округ",
    "Волновахский муниципальный округ",
    "Володарский муниципальный округ",
    "Добропольский муниципальный округ",
    "Константиновский муниципальный округ",
    "Красноармейский муниципальный округ",
    "Краснолиманский муниципальный округ",
    "Кураховский муниципальный округ",
    "Мангушский муниципальный округ",
    "Новоазовский муниципальный округ",
    "Славянский муниципальный округ",
    "Старобешевский муниципальный округ",
    "Тельмановский муниципальный округ",
    "Шахтерский муниципальный округ",
    "Ясиноватский муниципальный округ",
]
GO_LIST = [
    "городской округ Донецк",
    "городской округ Горловка",
    "городской округ Дебальцево",
    "городской округ Докучаевск",
    "городской округ Енакиево",
    "городской округ Иловайск",
    "городской округ Краматорск",
    "городской округ Макеевка",
    "городской округ Мариуполь",
    "городской округ Снежное",
    "городской округ Торез",
    "городской округ Харцызск",
]
FULL_LIST = MO_LIST + GO_LIST

# Соответствие старых названий в базе → новое по ОКТМО (для записей с геометрией)
RENAME_MAP = {
    "Донецкий район": "городской округ Донецк",
    "Горловский район": "городской округ Горловка",
    "Краматорский район": "городской округ Краматорск",
    "Мариупольский район": "городской округ Мариуполь",
    "Бахмутский район": "Артемовский муниципальный округ",
    "Покровский район": "Красноармейский муниципальный округ",
    # Волновахский муниципальный округ уже верный
}

with ENGINE.connect() as c:
    rid = str(c.execute(text("SELECT id FROM regions WHERE name = 'Донецкая Народная Республика'")).scalar())

# 1. Переименовать по RENAME_MAP
with ENGINE.begin() as c:
    for old_name, new_name in RENAME_MAP.items():
        c.execute(text("""
            UPDATE districts SET name = :new
            WHERE region_id = :rid AND name = :old
        """), {"rid": rid, "old": old_name, "new": new_name})
    print("Переименовано по соответствию:", list(RENAME_MAP.values()))

# 2. Удалить запись, которой нет в ОКТМО
with ENGINE.begin() as c:
    c.execute(text("""
        DELETE FROM districts WHERE region_id = :rid AND name = 'Кальмиусский район'
    """), {"rid": rid})
    print("Удалён (нет в ОКТМО): Кальмиусский район")

# 3. Добавить недостающие (без геометрии)
with ENGINE.connect() as c:
    existing = set(r[0] for r in c.execute(text("SELECT name FROM districts WHERE region_id = :rid"), {"rid": rid}).fetchall())
missing = [n for n in FULL_LIST if n not in existing]
print(f"Добавляю недостающие ({len(missing)}):", missing[:5], "..." if len(missing) > 5 else "")

with ENGINE.begin() as c:
    for name in missing:
        c.execute(text("""
            INSERT INTO districts (id, region_id, name) VALUES (:id, :rid, :name)
        """), {"id": str(uuid.uuid4()), "rid": rid, "name": name})
print("Готово.")

# Итог
with ENGINE.connect() as c:
    rows = c.execute(text("SELECT name FROM districts WHERE region_id = :rid ORDER BY name"), {"rid": rid}).fetchall()
    with_geom = c.execute(text("SELECT COUNT(*) FROM districts WHERE region_id = :rid AND geom IS NOT NULL AND ST_NPoints(geom)>0"), {"rid": rid}).scalar()
print(f"\nИтого по ДНР: {len(rows)} записей, из них с геометрией: {with_geom}")
for r in rows:
    print(f"  {r[0]}")
