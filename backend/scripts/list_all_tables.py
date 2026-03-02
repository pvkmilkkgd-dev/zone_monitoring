import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import psycopg

EXCLUDED = {"spatial_ref_sys", "geography_columns", "geometry_columns"}

conn = psycopg.connect("postgresql://postgres:postgres@localhost:5432/zone_monitoring")
cur = conn.cursor()

cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_type = 'BASE TABLE'
    ORDER BY table_name
""")

tables = [row[0] for row in cur.fetchall() if row[0] not in EXCLUDED]

for table in tables:
    cur.execute(f'SELECT COUNT(*) FROM "{table}"')
    count = cur.fetchone()[0]
    print(f"{table}: {count} rows")

cur.close()
conn.close()
