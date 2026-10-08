import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("releases", sa.Column("id", sa.String(100), primary_key=True),
                    sa.Column("manifest", sa.JSON(), nullable=False),
                    sa.Column("checksum", sa.String(64), nullable=False),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("player_stints", sa.Column("release_id", sa.String(100), sa.ForeignKey("releases.id"), primary_key=True),
                    sa.Column("id", sa.String(100), primary_key=True), sa.Column("team_id", sa.String(100), nullable=False),
                    sa.Column("league", sa.String(50), nullable=False), sa.Column("payload", sa.JSON(), nullable=False))
    op.create_index("ix_player_stints_team_id", "player_stints", ["team_id"])
    op.create_index("ix_player_stints_league", "player_stints", ["league"])
    op.create_table("teams", sa.Column("release_id", sa.String(100), sa.ForeignKey("releases.id"), primary_key=True),
                    sa.Column("id", sa.String(100), primary_key=True), sa.Column("payload", sa.JSON(), nullable=False))
    op.create_table("active_release", sa.Column("slot", sa.String(20), primary_key=True),
                    sa.Column("release_id", sa.String(100), sa.ForeignKey("releases.id"), nullable=False))


def downgrade():
    for table in ("active_release", "teams", "player_stints", "releases"):
        op.drop_table(table)
