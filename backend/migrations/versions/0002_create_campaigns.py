"""create campaigns

Revision ID: 0002_create_campaigns
Revises: 0001_create_users
Create Date: 2026-01-13 12:46:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "0002_create_campaigns"
down_revision = "0001_create_users"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("budget_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("budget_spent", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("buyer_cpc", sa.Numeric(12, 2), nullable=False),
        sa.Column("partner_payout", sa.Numeric(12, 2), nullable=False),
        sa.Column("targeting_category", sa.String(length=120)),
        sa.Column("targeting_geo", sa.String(length=120)),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_campaigns_buyer_id"), "campaigns", ["buyer_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_campaigns_buyer_id"), table_name="campaigns")
    op.drop_table("campaigns")
