"""Versioned private real-data evidence, separate from published releases."""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("evidence_imports", sa.Column("id", sa.String(100), primary_key=True),
                    sa.Column("manifest", sa.JSON(), nullable=False),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("source_records",
                    sa.Column("import_id", sa.String(100), sa.ForeignKey("evidence_imports.id"), primary_key=True),
                    sa.Column("id", sa.String(100), primary_key=True),
                    sa.Column("provider", sa.String(20), nullable=False),
                    sa.Column("name", sa.String(200), nullable=False),
                    sa.Column("league", sa.String(50), nullable=False),
                    sa.Column("season", sa.String(10), nullable=False),
                    sa.Column("payload", sa.JSON(), nullable=False))
    for field in ("provider", "name", "league"):
        op.create_index(f"ix_source_records_{field}", "source_records", [field])
    for table in ("source_features", "evidence_identity_links"):
        columns = [sa.Column("import_id", sa.String(100), primary_key=True),
                   sa.Column("record_id", sa.String(100), primary_key=True)]
        if table == "source_features":
            columns += [sa.Column("key", sa.String(60), primary_key=True),
                        sa.Column("value", sa.Float(), nullable=True),
                        sa.Column("status", sa.String(40), nullable=False),
                        sa.Column("payload", sa.JSON(), nullable=False)]
        else:
            columns += [sa.Column("canonical_id", sa.String(100), nullable=False),
                        sa.Column("review", sa.JSON(), nullable=False)]
        op.create_table(table, *columns, sa.ForeignKeyConstraint(
            ["import_id", "record_id"], ["source_records.import_id", "source_records.id"]))
    op.create_index("ix_evidence_identity_links_canonical_id", "evidence_identity_links", ["canonical_id"])
    op.create_table("active_evidence", sa.Column("slot", sa.String(20), primary_key=True),
                    sa.Column("import_id", sa.String(100), sa.ForeignKey("evidence_imports.id"), nullable=False))


def downgrade():
    for table in ("active_evidence", "evidence_identity_links", "source_features", "source_records", "evidence_imports"):
        op.drop_table(table)
