"""add event_comments table and is_archived field

Revision ID: add_event_comments_archived
Revises: add_updated_by_to_events
Create Date: 2026-01-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_event_comments_archived'
down_revision: Union[str, None] = 'add_updated_by_to_events'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем is_archived в events
    op.add_column('events', sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false', comment="Отметка 'не актуально'"))
    
    # Создаём таблицу комментариев
    op.create_table(
        'event_comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('text', sa.Text(), nullable=False, comment='Текст комментария'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_event_comments_id', 'event_comments', ['id'])
    op.create_index('ix_event_comments_event_id', 'event_comments', ['event_id'])


def downgrade() -> None:
    op.drop_index('ix_event_comments_event_id', table_name='event_comments')
    op.drop_index('ix_event_comments_id', table_name='event_comments')
    op.drop_table('event_comments')
    op.drop_column('events', 'is_archived')
