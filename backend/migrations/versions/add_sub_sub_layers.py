"""add sub_sub_layers table

Revision ID: add_sub_sub_layers
Revises: add_layers_tables
Create Date: 2026-01-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_sub_sub_layers'
down_revision = 'add_layers_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Таблица под-вложенных слоев (третий уровень)
    op.create_table(
        'sub_sub_layers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('parent_sub_layer_id', sa.Integer(), nullable=False),
        sa.Column('is_visible', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['parent_sub_layer_id'], ['sub_layers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sub_sub_layers_id'), 'sub_sub_layers', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_sub_sub_layers_id'), table_name='sub_sub_layers')
    op.drop_table('sub_sub_layers')
