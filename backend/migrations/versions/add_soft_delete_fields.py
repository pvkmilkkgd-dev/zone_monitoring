"""add is_deleted fields for soft delete

Revision ID: add_soft_delete_fields
Revises: add_event_comments_archived
Create Date: 2026-01-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_soft_delete_fields'
down_revision: Union[str, None] = 'add_event_comments_archived'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем is_deleted в layers
    op.add_column('layers', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false', comment='Мягкое удаление'))
    
    # Добавляем is_deleted в sub_layers
    op.add_column('sub_layers', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false', comment='Мягкое удаление'))
    
    # Добавляем is_deleted в sub_sub_layers
    op.add_column('sub_sub_layers', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false', comment='Мягкое удаление'))
    
    # Добавляем is_deleted в events
    op.add_column('events', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false', comment='Мягкое удаление'))
    
    # Добавляем is_deleted в administrative_zones
    op.add_column('administrative_zones', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false', comment='Мягкое удаление'))
    
    # Добавляем is_deleted в event_comments
    op.add_column('event_comments', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false', comment='Мягкое удаление'))


def downgrade() -> None:
    op.drop_column('event_comments', 'is_deleted')
    op.drop_column('administrative_zones', 'is_deleted')
    op.drop_column('events', 'is_deleted')
    op.drop_column('sub_sub_layers', 'is_deleted')
    op.drop_column('sub_layers', 'is_deleted')
    op.drop_column('layers', 'is_deleted')
