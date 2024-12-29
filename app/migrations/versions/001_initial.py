from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Audit table
    op.create_table('audits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(), nullable=True),
        sa.Column('status', sa.String(), server_default='pending', nullable=True),
        sa.Column('meta_title', sa.String(), nullable=True),
        sa.Column('meta_description', sa.String(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('audit_data', sa.Text(), nullable=True),
        sa.Column('suggestions_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audits_id'), 'audits', ['id'], unique=False)
    op.create_index(op.f('ix_audits_url'), 'audits', ['url'], unique=False)

    # AuditPage table
    op.create_table('audit_pages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('audit_id', sa.Integer(), nullable=True),
        sa.Column('url', sa.String(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('visited', sa.Boolean(), default=False, nullable=True),
        sa.Column('page_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['audit_id'], ['audits.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_pages_id'), 'audit_pages', ['id'], unique=False)
    op.create_index(op.f('ix_audit_pages_url'), 'audit_pages', ['url'], unique=False)

def downgrade() -> None:
    op.drop_table('audit_pages')
    op.drop_table('audits') 