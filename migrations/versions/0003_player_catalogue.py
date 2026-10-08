"""Mapped real player catalogue, independent from candidate publication."""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("catalogue_releases", sa.Column("id", sa.String(100), primary_key=True),
                    sa.Column("import_id", sa.String(100), sa.ForeignKey("evidence_imports.id"), nullable=False),
                    sa.Column("manifest", sa.JSON(), nullable=False))
    op.create_table("catalogue_players",
                    sa.Column("catalogue_id", sa.String(100), sa.ForeignKey("catalogue_releases.id"), primary_key=True),
                    sa.Column("id", sa.String(100), primary_key=True),
                    sa.Column("name", sa.String(200), nullable=False),
                    sa.Column("league", sa.String(50), nullable=False),
                    sa.Column("team", sa.String(200), nullable=False),
                    sa.Column("position", sa.String(20), nullable=False),
                    sa.Column("overall", sa.Float(), nullable=True),
                    sa.Column("payload", sa.JSON(), nullable=False))
    for field in ("name", "league", "team", "position", "overall"):
        op.create_index(f"ix_catalogue_players_{field}", "catalogue_players", [field])
    op.create_table("active_catalogue", sa.Column("slot", sa.String(20), primary_key=True),
                    sa.Column("catalogue_id", sa.String(100), sa.ForeignKey("catalogue_releases.id"), nullable=False))


def downgrade():
    op.drop_table("active_catalogue")
    op.drop_table("catalogue_players")
    op.drop_table("catalogue_releases")
