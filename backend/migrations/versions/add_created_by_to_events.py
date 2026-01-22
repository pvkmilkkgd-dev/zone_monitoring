"""add created_by to events

Revision ID: add_created_by_to_events
Revises: add_layer_to_events
Create Date: 2026-01-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_created_by_to_events'
down_revision = 'add_layer_to_events'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('events', sa.Column('created_by_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_events_created_by_id', 
        'events', 'users', 
        ['created_by_id'], ['id'], 
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_events_created_by_id', 'events', type_='foreignkey')
    op.drop_column('events', 'created_by_id')
