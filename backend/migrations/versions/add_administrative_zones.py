"""add administrative zones table

Revision ID: add_administrative_zones
Revises: add_full_name_users
Create Date: 2026-01-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_administrative_zones'
down_revision: Union[str, None] = 'add_full_name_users'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создание таблицы административных зон."""
    op.create_table(
        'administrative_zones',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('map_id', sa.Integer(), nullable=False),
        sa.Column('department_name', sa.String(length=255), nullable=False, comment='Название отдела'),
        sa.Column('district_names', sa.JSON(), nullable=False, comment='Список административных районов (JSON массив)'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['map_id'], ['maps.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_administrative_zones_id'), 'administrative_zones', ['id'], unique=False)


def downgrade() -> None:
    """Удаление таблицы административных зон."""
    op.drop_index(op.f('ix_administrative_zones_id'), table_name='administrative_zones')
    op.drop_table('administrative_zones')
