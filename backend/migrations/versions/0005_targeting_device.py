"""add targeting device placement

Revision ID: 0005_targeting_device
Revises: 0004_create_assignments_events
Create Date: 2026-01-13 13:22:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "0005_targeting_device"
down_revision = "0004_create_assignments_events"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("campaigns", sa.Column("targeting_device", sa.String(length=120)))
    op.add_column("campaigns", sa.Column("targeting_placement", sa.String(length=120)))


def downgrade():
    op.drop_column("campaigns", "targeting_placement")
    op.drop_column("campaigns", "targeting_device")
