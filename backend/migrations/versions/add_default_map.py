"""add default map seed data

Revision ID: add_default_map
Revises: add_layer_to_events
Create Date: 2026-01-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_default_map'
down_revision = 'add_layer_to_events'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем начальную карту с id=1
    op.execute("""
        INSERT INTO maps (id, name, description)
        VALUES (1, 'Основная карта', 'Карта регионов России')
        ON CONFLICT (id) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM maps WHERE id = 1")
