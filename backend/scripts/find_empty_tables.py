# -*- coding: utf-8 -*-
"""
Find all empty tables in zone_monitoring PostgreSQL database.
Shows columns, FK relationships, and which non-empty tables reference empty tables.
"""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"c:\Users\Lucky\Documents\zone_monitoring\backend")

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

CONN_STR = "postgresql://postgres:postgres@localhost:5432/zone_monitoring"


def main() -> None:
    with psycopg.connect(CONN_STR, row_factory=dict_row) as conn:
        # 1. Get all user tables in public schema with row counts
        with conn.cursor() as cur:
            cur.execute("""
                SELECT schemaname, relname AS table_name
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
                ORDER BY relname
            """)
            all_tables = [r["table_name"] for r in cur.fetchall()]

        # Get exact row counts for each table
        table_row_counts: dict[str, int] = {}
        for t in all_tables:
            with conn.cursor() as cur:
                cur.execute(sql.SQL("SELECT COUNT(*) AS cnt FROM {}").format(sql.Identifier(t)))
                table_row_counts[t] = cur.fetchone()["cnt"]

        empty_tables = [t for t in all_tables if table_row_counts[t] == 0]
        non_empty_tables = set(t for t in all_tables if table_row_counts[t] > 0)

        print("=" * 80)
        print("EMPTY TABLES IN zone_monitoring (0 rows)")
        print("=" * 80)
        print(f"\nTotal empty tables: {len(empty_tables)}")
        print(f"Total non-empty tables: {len(non_empty_tables)}")

        if not empty_tables:
            print("\nNo empty tables found.")
            return

        for table in sorted(empty_tables):
            print("\n" + "-" * 80)
            print(f"TABLE: {table}")
            print("-" * 80)

            # Columns
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position
                """, (table,))
                cols = cur.fetchall()

            print("\n  COLUMNS:")
            for c in cols:
                nullable = "NULL" if c["is_nullable"] == "YES" else "NOT NULL"
                default = f" DEFAULT {c['column_default']}" if c["column_default"] else ""
                print(f"    - {c['column_name']}: {c['data_type']} {nullable}{default}")

            # FKs where this table is the CHILD (references other tables)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        kcu.column_name,
                        ccu.table_name AS referenced_table,
                        ccu.column_name AS referenced_column,
                        tc.constraint_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage ccu
                        ON ccu.constraint_name = tc.constraint_name
                        AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_schema = 'public'
                        AND tc.table_name = %s
                """, (table,))
                outgoing_fks = cur.fetchall()

            print("\n  FOREIGN KEYS (this table references):")
            if outgoing_fks:
                for fk in outgoing_fks:
                    ref_table = fk["referenced_table"]
                    ref_rows = table_row_counts.get(ref_table, "?")
                    print(f"    - {fk['column_name']} -> {ref_table}.{fk['referenced_column']} ({ref_table} has {ref_rows} rows)")
            else:
                print("    (none)")

            # FKs where this table is the PARENT (other tables reference this)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        tc.table_name AS referencing_table,
                        kcu.column_name AS referencing_column,
                        ccu.column_name AS referenced_column,
                        tc.constraint_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage ccu
                        ON ccu.constraint_name = tc.constraint_name
                        AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_schema = 'public'
                        AND ccu.table_name = %s
                        AND ccu.table_schema = 'public'
                """, (table,))
                incoming_fks = cur.fetchall()

            print("\n  REFERENCED BY (tables that reference this empty table):")
            if incoming_fks:
                for fk in incoming_fks:
                    ref_table = fk["referencing_table"]
                    ref_rows = table_row_counts.get(ref_table, "?")
                    non_empty_marker = " [NON-EMPTY]" if ref_rows and ref_rows > 0 else " [EMPTY]"
                    print(f"    - {ref_table}.{fk['referencing_column']} -> {table}.{fk['referenced_column']} ({ref_table} has {ref_rows} rows){non_empty_marker}")
            else:
                print("    (none)")

            # Summary: non-empty tables that reference this empty table
            non_empty_refs = [
                fk["referencing_table"]
                for fk in incoming_fks
                if table_row_counts.get(fk["referencing_table"], 0) > 0
            ]
            if non_empty_refs:
                print("\n  *** WARNING: Non-empty tables referencing this empty table:")
                for t in sorted(set(non_empty_refs)):
                    print(f"      - {t} ({table_row_counts[t]} rows)")

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Empty tables: {', '.join(sorted(empty_tables))}")


if __name__ == "__main__":
    main()
