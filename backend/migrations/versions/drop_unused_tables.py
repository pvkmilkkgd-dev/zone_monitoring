"""drop unused tables

Revision ID: drop_unused_tables
Revises: add_audit_logs, add_default_map
Create Date: 2026-02-19
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "drop_unused_tables"
down_revision: Union[str, Sequence[str], None] = ("add_audit_logs", "add_default_map")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop children first to avoid FK conflicts.
    op.execute("DROP TABLE IF EXISTS device_positions;")
    op.execute("DROP TABLE IF EXISTS system_settings_regions;")
    op.execute("DROP TABLE IF EXISTS admin_centers;")
    op.execute("DROP TABLE IF EXISTS devices;")
    op.execute("DROP TABLE IF EXISTS regions_ref;")


def downgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS devices (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            name text NOT NULL,
            location geometry(Point,4326),
            region_id uuid REFERENCES regions(id),
            meta jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS devices_loc_gix ON devices USING gist (location);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS device_positions (
            id bigserial PRIMARY KEY,
            device_id uuid NOT NULL REFERENCES devices(id),
            ts timestamptz NOT NULL DEFAULT now(),
            location geometry(Point,4326) NOT NULL,
            meta jsonb NOT NULL DEFAULT '{}'::jsonb
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS device_positions_dev_ts ON device_positions (device_id, ts DESC);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS device_positions_loc_gix ON device_positions USING gist (location);"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_centers (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            district_id uuid REFERENCES districts(id),
            name varchar NOT NULL,
            population integer,
            created_at timestamptz NOT NULL DEFAULT now(),
            geom geometry(Point,4326)
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_admin_centers_district_id ON admin_centers (district_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_admin_centers_geom ON admin_centers USING gist (geom);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS system_settings_regions (
            settings_id smallint NOT NULL REFERENCES system_settings(id),
            region_id uuid NOT NULL REFERENCES regions(id),
            PRIMARY KEY (settings_id, region_id)
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS regions_ref (
            name text NOT NULL,
            geom geometry(MultiPolygon,4326)
        );
        """
    )
