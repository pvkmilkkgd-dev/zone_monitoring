from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = "081ea1895159"
down_revision = "106e368b601a"  # это наш users
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Таблица карт
    op.create_table(
        "maps",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("image_path", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )

    # Таблица зон
    op.create_table(
        "zones",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("map_id", sa.Integer, sa.ForeignKey("maps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("geometry", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )

    # Таблица событий по зонам
    op.create_table(
        "events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("map_id", sa.Integer, sa.ForeignKey("maps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("zone_id", sa.Integer, sa.ForeignKey("zones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("events")
    op.drop_table("zones")
    op.drop_table("maps")
