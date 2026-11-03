"""Add clients.country (country of registration). GST Number becomes mandatory for Indian entities.

Existing rows are backfilled: clients without a GST number that bill in USD are set to "US";
every other existing client defaults to "IN". Review backfilled clients in the UI if needed.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-03 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('clients') as batch:
        batch.add_column(sa.Column('country', sa.String(length=2), nullable=False, server_default='IN'))
    op.execute("UPDATE clients SET country = 'US' WHERE gst_number IS NULL AND billing_currency = 'USD'")


def downgrade() -> None:
    with op.batch_alter_table('clients') as batch:
        batch.drop_column('country')
