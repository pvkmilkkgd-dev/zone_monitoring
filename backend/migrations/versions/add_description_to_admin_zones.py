"""add description to administrative_zones

Revision ID: add_description_admin_zones
Revises: add_created_by_to_events
Create Date: 2026-01-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_description_admin_zones'
down_revision = 'add_created_by_to_events'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('administrative_zones', sa.Column('description', sa.Text(), nullable=True, comment='Описание подразделения'))


def downgrade() -> None:
    op.drop_column('administrative_zones', 'description')
