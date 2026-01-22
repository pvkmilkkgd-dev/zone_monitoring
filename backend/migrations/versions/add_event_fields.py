"""Add event fields: district_name, administrative_zone_id, importance, updated_at
Also create event_images and event_documents tables.

Revision ID: add_event_fields
Revises: add_districts_table
Create Date: 2026-01-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = 'add_event_fields'
down_revision = 'add_districts_table'
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем новые колонки в таблицу events
    op.add_column('events', sa.Column('district_name', sa.String(255), nullable=True))
    op.add_column('events', sa.Column('administrative_zone_id', sa.Integer(), nullable=True))
    op.add_column('events', sa.Column('importance', sa.Integer(), nullable=False, server_default='5'))
    op.add_column('events', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    
    # Добавляем внешний ключ
    op.create_foreign_key(
        'fk_events_administrative_zone_id',
        'events', 'administrative_zones',
        ['administrative_zone_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Создаём таблицу event_images
    op.create_table(
        'event_images',
        sa.Column('id', sa.BigInteger, primary_key=True),
        sa.Column('event_id', sa.BigInteger, sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.Text, nullable=False),
        sa.Column('file_path', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=func.now()),
    )
    
    # Создаём таблицу event_documents
    op.create_table(
        'event_documents',
        sa.Column('id', sa.BigInteger, primary_key=True),
        sa.Column('event_id', sa.BigInteger, sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.Text, nullable=False),
        sa.Column('file_path', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=func.now()),
    )


def downgrade():
    op.drop_table('event_documents')
    op.drop_table('event_images')
    op.drop_constraint('fk_events_administrative_zone_id', 'events', type_='foreignkey')
    op.drop_column('events', 'updated_at')
    op.drop_column('events', 'importance')
    op.drop_column('events', 'administrative_zone_id')
    op.drop_column('events', 'district_name')
