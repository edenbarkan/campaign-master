"""add click and impression events

Revision ID: 0006_click_impression_events
Revises: 0005_targeting_device
Create Date: 2026-01-13 14:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "0006_click_impression_events"
down_revision = "0005_targeting_device"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "click_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assignment_code", sa.String(length=64), nullable=False),
        sa.Column("partner_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id")),
        sa.Column("ad_id", sa.Integer(), sa.ForeignKey("ads.id")),
        sa.Column("ts", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=False),
        sa.Column("ua_hash", sa.String(length=64)),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reject_reason", sa.String(length=32)),
        sa.Column(
            "spend_delta",
            sa.Numeric(12, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "earnings_delta",
            sa.Numeric(12, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "profit_delta",
            sa.Numeric(12, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_click_events_assignment_code",
        "click_events",
        ["assignment_code"],
    )
    op.create_index(
        "ix_click_events_assignment_ip",
        "click_events",
        ["assignment_code", "ip_hash"],
    )

    op.create_table(
        "impression_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assignment_code", sa.String(length=64), nullable=False),
        sa.Column("partner_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id")),
        sa.Column("ad_id", sa.Integer(), sa.ForeignKey("ads.id")),
        sa.Column("ts", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("dedup_reason", sa.String(length=32)),
    )
    op.create_index(
        "ix_impression_events_assignment_code",
        "impression_events",
        ["assignment_code"],
    )
    op.create_index(
        "ix_impression_events_assignment_ip",
        "impression_events",
        ["assignment_code", "ip_hash"],
    )


def downgrade():
    op.drop_index("ix_impression_events_assignment_ip", table_name="impression_events")
    op.drop_index("ix_impression_events_assignment_code", table_name="impression_events")
    op.drop_table("impression_events")
    op.drop_index("ix_click_events_assignment_ip", table_name="click_events")
    op.drop_index("ix_click_events_assignment_code", table_name="click_events")
    op.drop_table("click_events")
