"""add district_descriptions table

Revision ID: add_district_descriptions
Revises: add_description_admin_zones
Create Date: 2026-01-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_district_descriptions'
down_revision = 'add_description_admin_zones'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'district_descriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('district_name', sa.String(length=255), nullable=False, comment='Название района'),
        sa.Column('description', sa.Text(), nullable=True, comment='Описание района'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_district_descriptions_district_name'), 'district_descriptions', ['district_name'], unique=True)
    op.create_index(op.f('ix_district_descriptions_id'), 'district_descriptions', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_district_descriptions_id'), table_name='district_descriptions')
    op.drop_index(op.f('ix_district_descriptions_district_name'), table_name='district_descriptions')
    op.drop_table('district_descriptions')
