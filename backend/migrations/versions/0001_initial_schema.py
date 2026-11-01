"""Initial schema: users/roles, clients, rate-card catalog, projects + versions,
job-category mappings, contracts, approval workflow and audit trail.

Revision ID: 0001
Revises: 
Create Date: 2026-10-31 10:26:16.875575
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('rate_cards',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.String(length=500), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_rate_cards')),
    sa.UniqueConstraint('code', name=op.f('uq_rate_cards_code'))
    )
    op.create_table('roles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.Enum('CRM', 'APPROVER', name='role_name', native_enum=False, length=32), nullable=False),
    sa.Column('description', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_roles')),
    sa.UniqueConstraint('name', name=op.f('uq_roles_name'))
    )
    op.create_table('job_categories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('default_rate_card_id', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['default_rate_card_id'], ['rate_cards.id'], name=op.f('fk_job_categories_default_rate_card_id_rate_cards')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_job_categories')),
    sa.UniqueConstraint('name', name=op.f('uq_job_categories_name'))
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=True),
    sa.Column('role_id', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name=op.f('fk_users_role_id_roles')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_role_id'), 'users', ['role_id'], unique=False)
    op.create_table('clients',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('legal_entity_name', sa.String(length=255), nullable=False),
    sa.Column('registered_address', sa.Text(), nullable=False),
    sa.Column('billing_address', sa.Text(), nullable=False),
    sa.Column('mode_of_payment', sa.String(length=64), nullable=False),
    sa.Column('gst_number', sa.String(length=15), nullable=True),
    sa.Column('billing_currency', sa.String(length=3), nullable=False),
    sa.Column('contact_name', sa.String(length=255), nullable=False),
    sa.Column('contact_designation', sa.String(length=255), nullable=False),
    sa.Column('contact_phone', sa.String(length=32), nullable=False),
    sa.Column('contact_email', sa.String(length=255), nullable=False),
    sa.Column('created_by_id', sa.Integer(), nullable=False),
    sa.Column('updated_by_id', sa.Integer(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_clients_created_by_id_users')),
    sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], name=op.f('fk_clients_updated_by_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_clients')),
    sa.UniqueConstraint('legal_entity_name', name=op.f('uq_clients_legal_entity_name'))
    )
    op.create_table('projects',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_code', sa.String(length=32), nullable=False),
    sa.Column('created_by_id', sa.Integer(), nullable=False),
    sa.Column('latest_version_number', sa.Integer(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_projects_created_by_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_projects')),
    sa.UniqueConstraint('project_code', name=op.f('uq_projects_project_code'))
    )
    op.create_index(op.f('ix_projects_created_by_id'), 'projects', ['created_by_id'], unique=False)
    op.create_table('project_versions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('version_number', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('DRAFT', 'PENDING_APPROVAL', 'REJECTED', 'APPROVED', name='version_status', native_enum=False, length=32), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('based_on_version_id', sa.Integer(), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=True),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.Column('business_unit', sa.String(length=128), nullable=True),
    sa.Column('crm_user_id', sa.Integer(), nullable=False),
    sa.Column('approver_id', sa.Integer(), nullable=True),
    sa.Column('client_id', sa.Integer(), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['approver_id'], ['users.id'], name=op.f('fk_project_versions_approver_id_users')),
    sa.ForeignKeyConstraint(['based_on_version_id'], ['project_versions.id'], name=op.f('fk_project_versions_based_on_version_id_project_versions')),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], name=op.f('fk_project_versions_client_id_clients')),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_project_versions_created_by_id_users')),
    sa.ForeignKeyConstraint(['crm_user_id'], ['users.id'], name=op.f('fk_project_versions_crm_user_id_users')),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_project_versions_project_id_projects'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_project_versions')),
    sa.UniqueConstraint('project_id', 'version_number', name='uq_project_versions_project_version')
    )
    op.create_index(op.f('ix_project_versions_approver_id'), 'project_versions', ['approver_id'], unique=False)
    op.create_index(op.f('ix_project_versions_client_id'), 'project_versions', ['client_id'], unique=False)
    op.create_index('ix_project_versions_status', 'project_versions', ['status'], unique=False)
    op.create_index('uq_project_versions_one_active', 'project_versions', ['project_id'], unique=True, postgresql_where=sa.text('is_active'), sqlite_where=sa.text('is_active = 1'))
    op.create_table('approval_requests',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('version_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='approval_status', native_enum=False, length=32), nullable=False),
    sa.Column('is_resubmission', sa.Boolean(), nullable=False),
    sa.Column('submitted_by_id', sa.Integer(), nullable=False),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('approver_id', sa.Integer(), nullable=False),
    sa.Column('decided_by_id', sa.Integer(), nullable=True),
    sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['approver_id'], ['users.id'], name=op.f('fk_approval_requests_approver_id_users')),
    sa.ForeignKeyConstraint(['decided_by_id'], ['users.id'], name=op.f('fk_approval_requests_decided_by_id_users')),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_approval_requests_project_id_projects'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['submitted_by_id'], ['users.id'], name=op.f('fk_approval_requests_submitted_by_id_users')),
    sa.ForeignKeyConstraint(['version_id'], ['project_versions.id'], name=op.f('fk_approval_requests_version_id_project_versions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_approval_requests'))
    )
    op.create_index('ix_approval_requests_approver_status', 'approval_requests', ['approver_id', 'status'], unique=False)
    op.create_index(op.f('ix_approval_requests_project_id'), 'approval_requests', ['project_id'], unique=False)
    op.create_index(op.f('ix_approval_requests_version_id'), 'approval_requests', ['version_id'], unique=False)
    op.create_table('audit_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=True),
    sa.Column('version_id', sa.Integer(), nullable=True),
    sa.Column('client_id', sa.Integer(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('action', sa.Enum('PROJECT_CREATED', 'PROJECT_UPDATED', 'CONTRACT_UPLOADED', 'CONTRACT_DELETED', 'SUBMITTED_FOR_APPROVAL', 'APPROVAL_ASSIGNED', 'PROJECT_APPROVED', 'PROJECT_REJECTED', 'PROJECT_RESUBMITTED', 'NEW_VERSION_CREATED', 'VERSION_ACTIVATED', 'CLIENT_CREATED', 'CLIENT_UPDATED', name='audit_action', native_enum=False, length=64), nullable=False),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('details', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], name=op.f('fk_audit_events_client_id_clients')),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_audit_events_project_id_projects'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_audit_events_user_id_users')),
    sa.ForeignKeyConstraint(['version_id'], ['project_versions.id'], name=op.f('fk_audit_events_version_id_project_versions'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_events'))
    )
    op.create_index(op.f('ix_audit_events_client_id'), 'audit_events', ['client_id'], unique=False)
    op.create_index('ix_audit_events_project_created', 'audit_events', ['project_id', 'created_at'], unique=False)
    op.create_table('contracts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('version_id', sa.Integer(), nullable=False),
    sa.Column('document_type', sa.String(length=64), nullable=False),
    sa.Column('valid_from', sa.Date(), nullable=False),
    sa.Column('valid_till', sa.Date(), nullable=False),
    sa.Column('file_name', sa.String(length=255), nullable=False),
    sa.Column('content_type', sa.String(length=128), nullable=False),
    sa.Column('size_bytes', sa.BigInteger(), nullable=False),
    sa.Column('checksum_sha256', sa.String(length=64), nullable=False),
    sa.Column('storage_key', sa.String(length=512), nullable=False),
    sa.Column('uploaded_by_id', sa.Integer(), nullable=False),
    sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id'], name=op.f('fk_contracts_uploaded_by_id_users')),
    sa.ForeignKeyConstraint(['version_id'], ['project_versions.id'], name=op.f('fk_contracts_version_id_project_versions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_contracts'))
    )
    op.create_index(op.f('ix_contracts_storage_key'), 'contracts', ['storage_key'], unique=False)
    op.create_index(op.f('ix_contracts_version_id'), 'contracts', ['version_id'], unique=False)
    op.create_table('project_job_categories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('version_id', sa.Integer(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('job_category_id', sa.Integer(), nullable=True),
    sa.Column('rate_card_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['job_category_id'], ['job_categories.id'], name=op.f('fk_project_job_categories_job_category_id_job_categories')),
    sa.ForeignKeyConstraint(['rate_card_id'], ['rate_cards.id'], name=op.f('fk_project_job_categories_rate_card_id_rate_cards')),
    sa.ForeignKeyConstraint(['version_id'], ['project_versions.id'], name=op.f('fk_project_job_categories_version_id_project_versions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_project_job_categories'))
    )
    op.create_index(op.f('ix_project_job_categories_version_id'), 'project_job_categories', ['version_id'], unique=False)
    op.create_table('approval_comments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('approval_request_id', sa.Integer(), nullable=False),
    sa.Column('author_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.Enum('SUBMISSION', 'APPROVAL', 'REJECTION', name='comment_kind', native_enum=False, length=32), nullable=False),
    sa.Column('comment', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['approval_request_id'], ['approval_requests.id'], name=op.f('fk_approval_comments_approval_request_id_approval_requests'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], name=op.f('fk_approval_comments_author_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_approval_comments'))
    )
    op.create_index(op.f('ix_approval_comments_approval_request_id'), 'approval_comments', ['approval_request_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_approval_comments_approval_request_id'), table_name='approval_comments')
    op.drop_table('approval_comments')
    op.drop_index(op.f('ix_project_job_categories_version_id'), table_name='project_job_categories')
    op.drop_table('project_job_categories')
    op.drop_index(op.f('ix_contracts_version_id'), table_name='contracts')
    op.drop_index(op.f('ix_contracts_storage_key'), table_name='contracts')
    op.drop_table('contracts')
    op.drop_index('ix_audit_events_project_created', table_name='audit_events')
    op.drop_index(op.f('ix_audit_events_client_id'), table_name='audit_events')
    op.drop_table('audit_events')
    op.drop_index(op.f('ix_approval_requests_version_id'), table_name='approval_requests')
    op.drop_index(op.f('ix_approval_requests_project_id'), table_name='approval_requests')
    op.drop_index('ix_approval_requests_approver_status', table_name='approval_requests')
    op.drop_table('approval_requests')
    op.drop_index('uq_project_versions_one_active', table_name='project_versions', postgresql_where=sa.text('is_active'), sqlite_where=sa.text('is_active = 1'))
    op.drop_index('ix_project_versions_status', table_name='project_versions')
    op.drop_index(op.f('ix_project_versions_client_id'), table_name='project_versions')
    op.drop_index(op.f('ix_project_versions_approver_id'), table_name='project_versions')
    op.drop_table('project_versions')
    op.drop_index(op.f('ix_projects_created_by_id'), table_name='projects')
    op.drop_table('projects')
    op.drop_table('clients')
    op.drop_index(op.f('ix_users_role_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_table('job_categories')
    op.drop_table('roles')
    op.drop_table('rate_cards')
