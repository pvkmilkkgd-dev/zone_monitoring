"""add audit_logs table

Revision ID: add_audit_logs
Revises: add_soft_delete_fields
Create Date: 2026-01-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_audit_logs'
down_revision: Union[str, None] = 'add_soft_delete_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('user_name', sa.String(255), nullable=True, comment='Имя пользователя на момент действия'),
        sa.Column('action', sa.String(50), nullable=False, comment='Тип действия'),
        sa.Column('entity_type', sa.String(100), nullable=True, comment='Тип сущности'),
        sa.Column('entity_id', sa.Integer(), nullable=True, comment='ID сущности'),
        sa.Column('entity_name', sa.String(255), nullable=True, comment='Название сущности на момент действия'),
        sa.Column('description', sa.Text(), nullable=True, comment='Описание действия'),
        sa.Column('details', sa.JSON(), nullable=True, comment='Дополнительные данные в формате JSON'),
        sa.Column('ip_address', sa.String(45), nullable=True, comment='IP адрес'),
        sa.Column('user_agent', sa.String(500), nullable=True, comment='User Agent браузера'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_entity_type', 'audit_logs', ['entity_type'])


def downgrade() -> None:
    op.drop_index('ix_audit_logs_entity_type', table_name='audit_logs')
    op.drop_index('ix_audit_logs_action', table_name='audit_logs')
    op.drop_index('ix_audit_logs_created_at', table_name='audit_logs')
    op.drop_index('ix_audit_logs_id', table_name='audit_logs')
    op.drop_table('audit_logs')
