"""drop legacy zones table

Revision ID: drop_zones_table
Revises: drop_unused_tables
Create Date: 2026-02-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "drop_zones_table"
down_revision: Union[str, Sequence[str], None] = "drop_unused_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The app does not use zone-based events anymore.
    op.drop_column("events", "zone_id")
    op.drop_table("zones")


def downgrade() -> None:
    op.create_table(
        "zones",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("geom", sa.Text(), nullable=True),
        sa.Column("center", sa.Text(), nullable=True),
        sa.Column("radius_m", sa.Integer(), nullable=True),
        sa.Column("region_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("events", sa.Column("zone_id", sa.Integer(), nullable=True))
