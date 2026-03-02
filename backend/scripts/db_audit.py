"""Database audit script for zone_monitoring PostgreSQL database."""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/zone_monitoring"
engine = create_engine(DB_URL)

SEP = "=" * 90


def section(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def get_columns(conn, table: str) -> list[str]:
    rows = conn.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = :t
        ORDER BY ordinal_position
    """), {"t": table}).fetchall()
    return [r[0] for r in rows]


def run():
    with engine.connect() as conn:
        # ── 1. All tables with row counts ──
        section("1. ALL TABLES WITH ROW COUNTS")

        tables = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)).fetchall()

        print(f"\nTotal tables: {len(tables)}\n")
        print(f"{'#':<4} {'Table':<40} {'Rows':>10}")
        print("-" * 56)

        table_counts = {}
        for idx, (tname,) in enumerate(tables, 1):
            cnt = conn.execute(text(f'SELECT COUNT(*) FROM "{tname}"')).scalar()
            table_counts[tname] = cnt
            print(f"{idx:<4} {tname:<40} {cnt:>10,}")

        # ── 2. Regions table ──
        section("2. REGIONS TABLE — ALL REGIONS")

        if "regions" not in table_counts:
            print("\n  Table 'regions' does not exist!")
        else:
            cols = get_columns(conn, "regions")
            print(f"\n  Columns: {', '.join(cols)}\n")

            geom_col = next((c for c in ("geom", "geometry") if c in cols), None)
            name_col = "name" if "name" in cols else None

            select_parts = ["id"]
            if name_col:
                select_parts.append(name_col)
            if "code" in cols:
                select_parts.append("code")
            if "is_active" in cols:
                select_parts.append("is_active")
            if geom_col:
                select_parts.append(
                    f"CASE WHEN {geom_col} IS NOT NULL THEN 'YES' ELSE 'NO' END AS has_geom"
                )
            if "geom_simplified" in cols:
                select_parts.append(
                    "CASE WHEN geom_simplified IS NOT NULL THEN 'YES' ELSE 'NO' END AS has_geom_simplified"
                )

            query = f"SELECT {', '.join(select_parts)} FROM regions ORDER BY id"
            rows = conn.execute(text(query)).fetchall()

            print(f"  Total regions: {len(rows)}\n")
            print(f"  {'ID':<40} {'Code':<12} {'Act':<5} {'Geom':<5} {'Simpl':<5} {'Name'}")
            print(f"  {'-'*40} {'-'*12} {'-'*5} {'-'*5} {'-'*5} {'-'*50}")

            for r in rows:
                m = dict(r._mapping)
                rid = str(m.get("id", ""))
                rname = str(m.get("name", ""))
                rcode = str(m.get("code", ""))
                active = str(m.get("is_active", ""))
                hg = str(m.get("has_geom", "N/A"))
                hs = str(m.get("has_geom_simplified", "N/A"))
                print(f"  {rid:<40} {rcode:<12} {active:<5} {hg:<5} {hs:<5} {rname}")

            with_geom = sum(1 for r in rows if dict(r._mapping).get("has_geom") == "YES")
            with_simpl = sum(1 for r in rows if dict(r._mapping).get("has_geom_simplified") == "YES")
            print(f"\n  Regions with geom: {with_geom} / {len(rows)}")
            print(f"  Regions with geom_simplified: {with_simpl} / {len(rows)}")

        # ── 3. Districts table ──
        section("3. DISTRICTS TABLE — PER-REGION BREAKDOWN")

        if "districts" not in table_counts:
            print("\n  Table 'districts' does not exist.")
        else:
            dcols = get_columns(conn, "districts")
            print(f"\n  Columns: {', '.join(dcols)}")
            print(f"  Total districts: {table_counts['districts']}\n")

            geom_col_d = next((c for c in ("geom", "geometry") if c in dcols), None)
            region_fk = next((c for c in ("region_id", "region_code") if c in dcols), None)
            name_col_d = next((c for c in ("name", "district_name") if c in dcols), None)

            if region_fk:
                geom_agg = ""
                if geom_col_d:
                    geom_agg = f", SUM(CASE WHEN d.{geom_col_d} IS NOT NULL THEN 1 ELSE 0 END)::int AS with_geom"

                join = ""
                rname_expr = f"d.{region_fk}::text"
                if "regions" in table_counts:
                    join = f"LEFT JOIN regions r ON d.{region_fk} = r.id"
                    rname_expr = "COALESCE(r.name, d." + region_fk + "::text)"

                query = f"""
                    SELECT d.{region_fk}, {rname_expr} AS region_name, COUNT(*) AS cnt{geom_agg}
                    FROM districts d {join}
                    GROUP BY d.{region_fk}, region_name
                    ORDER BY cnt DESC
                """
                rows = conn.execute(text(query)).fetchall()

                print(f"  Districts grouped by {region_fk} ({len(rows)} groups):\n")
                geom_header = ""
                if geom_col_d:
                    geom_header = f" {'w/Geom':>6} {'noGeom':>6}"
                print(f"  {region_fk:<38} {'Count':>5}{geom_header}  {'Region Name'}")
                print(f"  {'-'*38} {'-'*5}{' ' + '-'*6 + ' ' + '-'*6 if geom_col_d else ''}  {'-'*50}")

                total_with_geom = 0
                total_no_geom = 0
                for r in rows:
                    m = dict(r._mapping)
                    rfk = str(m[region_fk])[:36]
                    cnt = m["cnt"]
                    line = f"  {rfk:<38} {cnt:>5}"
                    if geom_col_d:
                        wg = m["with_geom"]
                        ng = cnt - wg
                        total_with_geom += wg
                        total_no_geom += ng
                        line += f" {wg:>6} {ng:>6}"
                    line += f"  {m['region_name']}"
                    print(line)

                if geom_col_d:
                    print(f"\n  Total districts with geometry: {total_with_geom}")
                    print(f"  Total districts without geometry: {total_no_geom}")
            else:
                print("  No region foreign key column found in districts table.")
                if geom_col_d:
                    wg = conn.execute(text(
                        f"SELECT COUNT(*) FROM districts WHERE {geom_col_d} IS NOT NULL"
                    )).scalar()
                    print(f"  Districts with geometry: {wg} / {table_counts['districts']}")

        # ── 3b. Administrative zones ──
        if "administrative_zones" in table_counts and table_counts["administrative_zones"] > 0:
            section("3b. ADMINISTRATIVE ZONES")
            az_cols = get_columns(conn, "administrative_zones")
            print(f"\n  Columns: {', '.join(az_cols)}")
            print(f"  Total rows: {table_counts['administrative_zones']}\n")

            rows = conn.execute(text("""
                SELECT id, department_name, map_id, district_names, is_deleted
                FROM administrative_zones
                ORDER BY id
            """)).fetchall()

            print(f"  {'ID':<6} {'Map':<6} {'Del':<5} {'Department':<40} {'Districts (JSON)'}")
            print(f"  {'-'*6} {'-'*6} {'-'*5} {'-'*40} {'-'*30}")
            for r in rows:
                dp = str(r[3])[:60] + ("..." if len(str(r[3])) > 60 else "")
                print(f"  {r[0]:<6} {r[2]:<6} {str(r[4]):<5} {str(r[1])[:38]:<40} {dp}")

        # ── 4. System settings ──
        section("4. SYSTEM SETTINGS")

        for tname in ("system_settings", "system_settings_regions"):
            if tname not in table_counts:
                continue
            cols = get_columns(conn, tname)
            print(f"\n  --- {tname} ({table_counts[tname]} rows) ---")
            print(f"  Columns: {', '.join(cols)}")

            if table_counts[tname] == 0:
                print("  (empty)")
                continue

            rows = conn.execute(text(f"SELECT * FROM {tname} ORDER BY id")).fetchall()
            for r in rows:
                m = dict(r._mapping)
                for k, v in m.items():
                    print(f"    {k}: {v}")
                print()

        # ── 5. Orphan / integrity checks ──
        section("5. ORPHAN / INTEGRITY CHECKS")

        checks_done = 0

        # regions → (no map_id in actual schema, skip if not present)
        r_cols = get_columns(conn, "regions") if "regions" in table_counts else []

        # Use text casts to avoid UUID/integer type mismatches across tables
        def safe_orphan_count(sql: str) -> int | None:
            try:
                return conn.execute(text(sql)).scalar()
            except Exception as e:
                print(f"    ⚠ Query failed: {e}")
                return None

        def safe_orphan_rows(sql: str):
            try:
                return conn.execute(text(sql)).fetchall()
            except Exception as e:
                print(f"    ⚠ Query failed: {e}")
                return []

        # districts → regions
        d_cols = get_columns(conn, "districts") if "districts" in table_counts else []
        if "region_id" in d_cols and "regions" in table_counts:
            orphans = safe_orphan_rows("""
                SELECT d.id, d.region_id
                FROM districts d
                LEFT JOIN regions r ON d.region_id::text = r.id::text
                WHERE r.id IS NULL
            """)
            print(f"\n  [districts → regions] Orphaned (non-existent region): {len(orphans)}")
            for o in orphans[:20]:
                print(f"    district id={o[0]} → region_id={o[1]} (MISSING)")
            if len(orphans) > 20:
                print(f"    ... and {len(orphans) - 20} more")
            checks_done += 1

        # events → maps
        if "events" in table_counts and table_counts["events"] > 0:
            e_cols = get_columns(conn, "events")

            if "map_id" in e_cols:
                n = safe_orphan_count("""
                    SELECT COUNT(*) FROM events e
                    LEFT JOIN maps m ON e.map_id::text = m.id::text WHERE m.id IS NULL
                """)
                print(f"\n  [events → maps] Orphaned: {n}")
                checks_done += 1

            if "zone_id" in e_cols:
                n = safe_orphan_count("""
                    SELECT COUNT(*) FROM events e
                    WHERE e.zone_id IS NOT NULL
                      AND NOT EXISTS (SELECT 1 FROM zones z WHERE z.id::text = e.zone_id::text)
                """)
                print(f"  [events → zones] Orphaned: {n}")
                checks_done += 1

            if "administrative_zone_id" in e_cols:
                n = safe_orphan_count("""
                    SELECT COUNT(*) FROM events e
                    WHERE e.administrative_zone_id IS NOT NULL
                      AND NOT EXISTS (SELECT 1 FROM administrative_zones az WHERE az.id::text = e.administrative_zone_id::text)
                """)
                print(f"  [events → admin_zones] Orphaned: {n}")
                checks_done += 1

            if "created_by_id" in e_cols:
                n = safe_orphan_count("""
                    SELECT COUNT(*) FROM events e
                    WHERE e.created_by_id IS NOT NULL
                      AND NOT EXISTS (SELECT 1 FROM users u WHERE u.id::text = e.created_by_id::text)
                """)
                print(f"  [events → users (created_by)] Orphaned: {n}")
                checks_done += 1

        # zones → maps
        z_cols = get_columns(conn, "zones") if "zones" in table_counts else []
        if "map_id" in z_cols:
            n = safe_orphan_count("""
                SELECT COUNT(*) FROM zones z
                LEFT JOIN maps m ON z.map_id::text = m.id::text WHERE m.id IS NULL
            """)
            print(f"\n  [zones → maps] Orphaned: {n}")
            checks_done += 1

        # administrative_zones → maps
        az_cols_list = get_columns(conn, "administrative_zones") if "administrative_zones" in table_counts else []
        if "map_id" in az_cols_list:
            n = safe_orphan_count("""
                SELECT COUNT(*) FROM administrative_zones az
                LEFT JOIN maps m ON az.map_id::text = m.id::text WHERE m.id IS NULL
            """)
            print(f"  [admin_zones → maps] Orphaned: {n}")
            checks_done += 1

        # zone_states → zones
        if "zone_states" in table_counts and table_counts["zone_states"] > 0:
            n = safe_orphan_count("""
                SELECT COUNT(*) FROM zone_states zs
                WHERE NOT EXISTS (SELECT 1 FROM zones z WHERE z.id::text = zs.zone_id::text)
            """)
            print(f"  [zone_states → zones] Orphaned: {n}")
            checks_done += 1

        # layers → maps
        l_cols = get_columns(conn, "layers") if "layers" in table_counts else []
        if "map_id" in l_cols:
            n = safe_orphan_count("""
                SELECT COUNT(*) FROM layers l
                LEFT JOIN maps m ON l.map_id::text = m.id::text WHERE m.id IS NULL
            """)
            print(f"  [layers → maps] Orphaned: {n}")
            checks_done += 1

        # sub_layers → layers
        if "sub_layers" in table_counts:
            sl_cols = get_columns(conn, "sub_layers")
            if "parent_layer_id" in sl_cols:
                n = safe_orphan_count("""
                    SELECT COUNT(*) FROM sub_layers sl
                    WHERE NOT EXISTS (SELECT 1 FROM layers l WHERE l.id::text = sl.parent_layer_id::text)
                """)
                print(f"  [sub_layers → layers] Orphaned: {n}")
                checks_done += 1

        # sub_sub_layers → sub_layers
        if "sub_sub_layers" in table_counts:
            ssl_cols = get_columns(conn, "sub_sub_layers")
            if "parent_sub_layer_id" in ssl_cols:
                n = safe_orphan_count("""
                    SELECT COUNT(*) FROM sub_sub_layers ssl
                    WHERE NOT EXISTS (SELECT 1 FROM sub_layers sl WHERE sl.id::text = ssl.parent_sub_layer_id::text)
                """)
                print(f"  [sub_sub_layers → sub_layers] Orphaned: {n}")
                checks_done += 1

        # Duplicate region names
        if "regions" in table_counts:
            dupes = conn.execute(text("""
                SELECT name, COUNT(*) AS cnt
                FROM regions
                GROUP BY name
                HAVING COUNT(*) > 1
                ORDER BY cnt DESC
            """)).fetchall()
            print(f"\n  [regions] Duplicate names: {len(dupes)}")
            for d in dupes[:10]:
                print(f"    name='{d[0]}' count={d[1]}")

        # Duplicate district names per region
        if "districts" in table_counts and "region_id" in d_cols and name_col_d:
            dupes = conn.execute(text(f"""
                SELECT region_id, {name_col_d}, COUNT(*) AS cnt
                FROM districts
                GROUP BY region_id, {name_col_d}
                HAVING COUNT(*) > 1
                ORDER BY cnt DESC
                LIMIT 20
            """)).fetchall()
            print(f"\n  [districts] Duplicate names within same region: {len(dupes)}")
            for d in dupes[:10]:
                print(f"    region_id={d[0]} name='{d[1]}' count={d[2]}")
            if len(dupes) > 10:
                print(f"    ... and {len(dupes) - 10} more")

        # Regions with NULL geom
        if "regions" in table_counts and "geom" in r_cols:
            n = conn.execute(text("SELECT COUNT(*) FROM regions WHERE geom IS NULL")).scalar()
            print(f"\n  [regions] With NULL geom: {n} / {table_counts['regions']}")

        # Districts with NULL geom
        if "districts" in table_counts and geom_col_d:
            n = conn.execute(text(
                f"SELECT COUNT(*) FROM districts WHERE {geom_col_d} IS NULL"
            )).scalar()
            print(f"  [districts] With NULL geom: {n} / {table_counts['districts']}")

        if checks_done == 0:
            print("\n  No foreign key relationships to check.")

        # ── Appendix: Maps ──
        section("APPENDIX A: MAPS")
        if "maps" in table_counts:
            m_cols = get_columns(conn, "maps")
            print(f"\n  Columns: {', '.join(m_cols)}\n")
            rows = conn.execute(text("SELECT * FROM maps ORDER BY id")).fetchall()
            for r in rows:
                m = dict(r._mapping)
                for k, v in m.items():
                    val = str(v)[:100] if v is not None else "NULL"
                    print(f"    {k}: {val}")
                print()

        # ── Appendix: Regions reference table ──
        if "regions_ref" in table_counts and table_counts["regions_ref"] > 0:
            section("APPENDIX B: REGIONS_REF TABLE")
            ref_cols = get_columns(conn, "regions_ref")
            print(f"\n  Columns: {', '.join(ref_cols)}")
            print(f"  Total rows: {table_counts['regions_ref']}\n")

            non_geom = [c for c in ref_cols if c not in ("geom", "geom_simplified", "geometry", "bbox")]
            if non_geom:
                select = ", ".join(non_geom)
                order_col = non_geom[0]
                rows = conn.execute(text(f"SELECT {select} FROM regions_ref ORDER BY {order_col} LIMIT 15")).fetchall()
                print(f"  (First 15 rows, geometry columns excluded)")
                for r in rows:
                    m = dict(r._mapping)
                    parts = [f"{k}={v}" for k, v in m.items()]
                    print(f"    {' | '.join(parts)}")
            else:
                print("  (only geometry columns — skipping preview)")

        # ── Appendix: Users ──
        if "users" in table_counts and table_counts["users"] > 0:
            section("APPENDIX C: USERS")
            u_cols = get_columns(conn, "users")
            print(f"\n  Columns: {', '.join(u_cols)}")
            safe_cols = [c for c in u_cols if c not in ("hashed_password", "password_hash", "password")]
            rows = conn.execute(text(
                f"SELECT {', '.join(safe_cols)} FROM users ORDER BY id"
            )).fetchall()
            print(f"  Total: {len(rows)}\n")
            for r in rows:
                m = dict(r._mapping)
                parts = [f"{k}={v}" for k, v in m.items()]
                print(f"    {' | '.join(parts)}")

    print(f"\n{SEP}")
    print("  AUDIT COMPLETE")
    print(f"{SEP}\n")


if __name__ == "__main__":
    run()
