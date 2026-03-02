"""Check districts table structure."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text, inspect
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
inspector = inspect(engine)

# Check all tables
tables = inspector.get_table_names()
print("Таблицы в БД:")
for t in sorted(tables):
    print(f"  - {t}")

# Check districts table
if 'districts' in tables:
    print("\nСтруктура таблицы 'districts':")
    for col in inspector.get_columns('districts'):
        nullable = "NULL" if col.get('nullable') else "NOT NULL"
        print(f"  {col['name']}: {col['type']} {nullable}")
    
    # Check row count
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM districts")).scalar()
        print(f"\nКоличество записей: {result}")
else:
    print("\nТаблица 'districts' НЕ НАЙДЕНА!")
