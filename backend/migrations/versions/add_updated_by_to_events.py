"""add updated_by_id to events

Revision ID: add_updated_by_to_events
Revises: add_district_descriptions_table
Create Date: 2026-01-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_updated_by_to_events'
down_revision: Union[str, None] = 'add_district_descriptions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('events', sa.Column('updated_by_id', sa.Integer(), nullable=True, comment='ID пользователя изменившего событие'))
    op.create_foreign_key(
        'fk_events_updated_by_id',
        'events', 'users',
        ['updated_by_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_events_updated_by_id', 'events', type_='foreignkey')
    op.drop_column('events', 'updated_by_id')
