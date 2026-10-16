"""Seed default posture domain mappings."""

from alembic import op


revision = "0002_seed_domain_mapping_defaults"
down_revision = "0001_posture_domain_lookup"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        INSERT INTO posture_domain_mapping (tool, service, category, domain)
        VALUES
        -- Cloud posture (prowler)
        ('prowler','iam',NULL,'identity'),
        ('prowler','s3',NULL,'cloud'),
        ('prowler','ec2',NULL,'cloud'),
        ('prowler','vpc',NULL,'cloud'),
        ('prowler','rds',NULL,'cloud'),
        ('prowler','eks',NULL,'cloud'),
        (NULL,NULL,'iam','identity'),
        (NULL,NULL,'network','cloud'),
        (NULL,NULL,'storage','cloud'),
        (NULL,NULL,'db','cloud'),
        -- App security
        ('semgrep',NULL,NULL,'app'),
        ('checkov',NULL,NULL,'app'),
        ('gitleaks',NULL,NULL,'app'),
        ('trivy',NULL,NULL,'app'),
        ('zap',NULL,NULL,'app'),
        -- Endpoint
        (NULL,NULL,'endpoint','endpoint'),
        (NULL,NULL,'edr','endpoint'),
        -- AI
        (NULL,NULL,'ai','ai')
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade():
    # No-op rollback for seed data
    pass

