"""Create posture score snapshot tables."""

from alembic import op
import sqlalchemy as sa

revision = "0003_posture_score_snapshots"
down_revision = "0002_seed_domain_mapping_defaults"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "posture_score_snapshot",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("coverage", sa.JSON(), nullable=True),
        sa.Column("incident_penalty", sa.Integer(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
    )
    op.create_index("idx_posture_score_snapshot_tenant", "posture_score_snapshot", ["tenant_id"])

    op.create_table(
        "posture_domain_score_snapshot",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("snapshot_id", sa.UUID(), sa.ForeignKey("posture_score_snapshot.id", ondelete="CASCADE")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("domain", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("score_adjusted", sa.Integer(), nullable=True),
        sa.Column("coverage", sa.Float(), nullable=True),
        sa.Column("risk", sa.Integer(), nullable=True),
        sa.Column("open_count", sa.Integer(), nullable=True),
        sa.Column("counts", sa.JSON(), nullable=True),
    )
    op.create_index("idx_posture_domain_score_snapshot_tenant", "posture_domain_score_snapshot", ["tenant_id"])


def downgrade():
    op.drop_index("idx_posture_domain_score_snapshot_tenant", table_name="posture_domain_score_snapshot")
    op.drop_table("posture_domain_score_snapshot")
    op.drop_index("idx_posture_score_snapshot_tenant", table_name="posture_score_snapshot")
    op.drop_table("posture_score_snapshot")

