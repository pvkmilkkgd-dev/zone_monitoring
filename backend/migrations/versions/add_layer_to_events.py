"""add layer fields to events

Revision ID: add_layer_to_events
Revises: add_layer_to_admin_zones
Create Date: 2026-01-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_layer_to_events'
down_revision = 'add_layer_to_admin_zones'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('events', sa.Column('layer_id', sa.Integer(), nullable=True))
    op.add_column('events', sa.Column('sub_layer_id', sa.Integer(), nullable=True))
    op.add_column('events', sa.Column('sub_sub_layer_id', sa.Integer(), nullable=True))
    
    op.create_foreign_key(
        'fk_events_layer_id', 
        'events', 'layers', 
        ['layer_id'], ['id'], 
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_events_sub_layer_id', 
        'events', 'sub_layers', 
        ['sub_layer_id'], ['id'], 
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_events_sub_sub_layer_id', 
        'events', 'sub_sub_layers', 
        ['sub_sub_layer_id'], ['id'], 
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_events_sub_sub_layer_id', 'events', type_='foreignkey')
    op.drop_constraint('fk_events_sub_layer_id', 'events', type_='foreignkey')
    op.drop_constraint('fk_events_layer_id', 'events', type_='foreignkey')
    op.drop_column('events', 'sub_sub_layer_id')
    op.drop_column('events', 'sub_layer_id')
    op.drop_column('events', 'layer_id')
