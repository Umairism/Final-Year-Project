"""Persist patient emergency contacts.

Revision ID: e34a20261026
Revises: c8f92a104b91
"""
from alembic import op
import sqlalchemy as sa

revision = 'e34a20261026'
down_revision = 'c8f92a104b91'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('patients') as batch:
        batch.add_column(sa.Column('emergency_contacts', sa.JSON(),
                                   server_default=sa.text("'[]'"), nullable=False))


def downgrade():
    with op.batch_alter_table('patients') as batch:
        batch.drop_column('emergency_contacts')
