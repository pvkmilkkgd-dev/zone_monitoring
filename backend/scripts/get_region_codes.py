"""Get current region list from DB and map to ОКТМО codes on classinform.ru"""
import sys, os
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)

with ENGINE.connect() as c:
    rows = c.execute(text("SELECT id, name FROM regions ORDER BY name")).fetchall()

print(f"Total regions in DB: {len(rows)}")
for rid, rname in rows:
    print(f"  {rid}: {rname}")
