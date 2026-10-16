"""Add asset criticality and data classification to asset tables."""

from alembic import op
import sqlalchemy as sa

revision = "0004_asset_criticality_classification"
down_revision = "0003_posture_score_snapshots"
branch_labels = None
depends_on = None


def upgrade():
    for table in ["customer_cloud_accounts", "git_repositories", "customer_endpoint_agents"]:
        op.add_column(table, sa.Column("criticality", sa.String(length=32), nullable=True))
        op.add_column(table, sa.Column("data_classification", sa.String(length=64), nullable=True))


def downgrade():
    for table in ["customer_endpoint_agents", "git_repositories", "customer_cloud_accounts"]:
        op.drop_column(table, "data_classification")
        op.drop_column(table, "criticality")

