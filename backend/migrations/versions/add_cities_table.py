"""add cities table for region settlements

Revision ID: add_cities_table
Revises: drop_zones_table
Create Date: 2026-02-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "add_cities_table"
down_revision: Union[str, None] = "drop_zones_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS cities (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            region_id UUID NOT NULL REFERENCES regions(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            population INTEGER DEFAULT 0,
            lat DOUBLE PRECISION NOT NULL,
            lon DOUBLE PRECISION NOT NULL,
            importance INTEGER NOT NULL DEFAULT 5
        );
        CREATE INDEX IF NOT EXISTS idx_cities_region_id ON cities(region_id);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS cities;")
