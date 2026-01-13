"""create assignments and events

Revision ID: 0004_create_assignments_events
Revises: 0003_create_ads
Create Date: 2026-01-13 12:54:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "0004_create_assignments_events"
down_revision = "0003_create_ads"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ad_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("partner_id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("ad_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=120)),
        sa.Column("geo", sa.String(length=120)),
        sa.Column("placement", sa.String(length=120)),
        sa.Column("device", sa.String(length=120)),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["partner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ad_id"], ["ads.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("code", name="uq_ad_assignments_code"),
    )
    op.create_index(op.f("ix_ad_assignments_code"), "ad_assignments", ["code"], unique=True)
    op.create_index(
        op.f("ix_ad_assignments_partner_id"),
        "ad_assignments",
        ["partner_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ad_assignments_campaign_id"),
        "ad_assignments",
        ["campaign_id"],
        unique=False,
    )

    op.create_table(
        "tracking_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("ad_id", sa.Integer(), nullable=False),
        sa.Column("partner_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id"], ["ad_assignments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ad_id"], ["ads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        op.f("ix_tracking_events_created_at"),
        "tracking_events",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tracking_events_event_type"),
        "tracking_events",
        ["event_type"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_tracking_events_event_type"), table_name="tracking_events")
    op.drop_index(op.f("ix_tracking_events_created_at"), table_name="tracking_events")
    op.drop_table("tracking_events")
    op.drop_index(op.f("ix_ad_assignments_campaign_id"), table_name="ad_assignments")
    op.drop_index(op.f("ix_ad_assignments_partner_id"), table_name="ad_assignments")
    op.drop_index(op.f("ix_ad_assignments_code"), table_name="ad_assignments")
    op.drop_table("ad_assignments")
