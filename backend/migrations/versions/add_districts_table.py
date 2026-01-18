"""add districts table

Revision ID: add_districts_table
Revises: add_administrative_zones
Create Date: 2026-01-17 11:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

# revision identifiers, used by Alembic.
revision = 'add_districts_table'
down_revision = 'add_administrative_zones'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    
    op.create_table(
        'districts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('region_id', UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('osm_id', sa.BigInteger, nullable=True),
        sa.Column('admin_level', sa.Integer, nullable=True),
        sa.Column('population', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Добавляем геометрию через PostGIS
    op.execute("""
        SELECT AddGeometryColumn('districts', 'geom', 4326, 'MULTIPOLYGON', 2);
        SELECT AddGeometryColumn('districts', 'geom_simplified', 4326, 'MULTIPOLYGON', 2);
    """)
    
    # Создаем индексы
    op.execute("CREATE INDEX idx_districts_region_id ON districts(region_id)")
    op.execute("CREATE INDEX idx_districts_geom ON districts USING GIST(geom)")
    op.execute("CREATE INDEX idx_districts_geom_simplified ON districts USING GIST(geom_simplified)")


def downgrade() -> None:
    op.drop_table('districts')
