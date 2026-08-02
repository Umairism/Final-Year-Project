"""add telemetry metadata fields

Revision ID: c8f92a104b91
Revises: b52623274ba1
Create Date: 2026-08-02 04:03:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8f92a104b91'
down_revision: Union[str, None] = 'b52623274ba1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create Enum type for BpSource
    bp_source_enum = sa.Enum('manual_entry', 'ble_cuff', 'hardware_uart', 'none', name='bpsource')
    bp_source_enum.create(op.get_bind(), checkfirst=True)

    op.add_column('vital_signs', sa.Column('bp_source', bp_source_enum, server_default='none', nullable=False))
    op.add_column('vital_signs', sa.Column('delayed_sync', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('devices', sa.Column('api_key_hash', sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column('devices', 'api_key_hash')
    op.drop_column('vital_signs', 'delayed_sync')
    op.drop_column('vital_signs', 'bp_source')
    
    bp_source_enum = sa.Enum(name='bpsource')
    bp_source_enum.drop(op.get_bind(), checkfirst=True)
