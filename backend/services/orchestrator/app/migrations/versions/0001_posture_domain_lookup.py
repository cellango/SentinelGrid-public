"""Add posture domain mapping and severity weight lookups"""

from alembic import op
import sqlalchemy as sa


revision = '0001_posture_domain_lookup'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'posture_domain_mapping',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('tool', sa.String(length=64), nullable=True),
        sa.Column('service', sa.String(length=128), nullable=True),
        sa.Column('category', sa.String(length=128), nullable=True),
        sa.Column('domain', sa.String(length=32), nullable=False),
    )
    op.create_index('idx_posture_domain_mapping_lookup', 'posture_domain_mapping', ['tool', 'service', 'category'], unique=False)

    op.create_table(
        'posture_severity_weight',
        sa.Column('severity', sa.String(length=32), primary_key=True),
        sa.Column('weight', sa.Integer, nullable=False),
    )

    # Seed default severity weights
    op.execute("""
        INSERT INTO posture_severity_weight (severity, weight) VALUES
        ('critical', 40),
        ('high', 20),
        ('medium', 5),
        ('low', 1),
        ('info', 0)
        ON CONFLICT (severity) DO NOTHING;
    """)


def downgrade():
    op.drop_table('posture_severity_weight')
    op.drop_index('idx_posture_domain_mapping_lookup', table_name='posture_domain_mapping')
    op.drop_table('posture_domain_mapping')

