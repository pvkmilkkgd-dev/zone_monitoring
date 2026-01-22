"""add layers tables

Revision ID: add_layers_tables
Revises: add_event_fields
Create Date: 2026-01-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_layers_tables'
down_revision = 'add_event_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Таблица главных слоев
    op.create_table(
        'layers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('map_id', sa.Integer(), nullable=False),
        sa.Column('is_visible', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['map_id'], ['maps.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_layers_id'), 'layers', ['id'], unique=False)
    
    # Таблица вложенных слоев
    op.create_table(
        'sub_layers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('parent_layer_id', sa.Integer(), nullable=False),
        sa.Column('is_visible', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['parent_layer_id'], ['layers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sub_layers_id'), 'sub_layers', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_sub_layers_id'), table_name='sub_layers')
    op.drop_table('sub_layers')
    op.drop_index(op.f('ix_layers_id'), table_name='layers')
    op.drop_table('layers')
