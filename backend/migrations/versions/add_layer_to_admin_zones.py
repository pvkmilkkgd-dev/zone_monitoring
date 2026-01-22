"""add layer fields to administrative_zones

Revision ID: add_layer_to_admin_zones
Revises: add_sub_sub_layers
Create Date: 2026-01-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_layer_to_admin_zones'
down_revision = 'add_sub_sub_layers'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('administrative_zones', sa.Column('layer_id', sa.Integer(), nullable=True))
    op.add_column('administrative_zones', sa.Column('sub_layer_id', sa.Integer(), nullable=True))
    op.add_column('administrative_zones', sa.Column('sub_sub_layer_id', sa.Integer(), nullable=True))
    
    op.create_foreign_key(
        'fk_admin_zones_layer_id', 
        'administrative_zones', 'layers', 
        ['layer_id'], ['id'], 
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_admin_zones_sub_layer_id', 
        'administrative_zones', 'sub_layers', 
        ['sub_layer_id'], ['id'], 
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_admin_zones_sub_sub_layer_id', 
        'administrative_zones', 'sub_sub_layers', 
        ['sub_sub_layer_id'], ['id'], 
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_admin_zones_sub_sub_layer_id', 'administrative_zones', type_='foreignkey')
    op.drop_constraint('fk_admin_zones_sub_layer_id', 'administrative_zones', type_='foreignkey')
    op.drop_constraint('fk_admin_zones_layer_id', 'administrative_zones', type_='foreignkey')
    op.drop_column('administrative_zones', 'sub_sub_layer_id')
    op.drop_column('administrative_zones', 'sub_layer_id')
    op.drop_column('administrative_zones', 'layer_id')
