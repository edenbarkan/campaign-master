"""add partner ad request events and exposures

Revision ID: 0007_partner_requests
Revises: 0006_click_impression_events
Create Date: 2026-01-13 15:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "0007_partner_requests"
down_revision = "0006_click_impression_events"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "partner_ad_request_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("partner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("placement", sa.String(length=120)),
        sa.Column("device", sa.String(length=120)),
        sa.Column("geo", sa.String(length=120)),
        sa.Column("category", sa.String(length=120)),
        sa.Column("filled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("ad_id", sa.Integer(), sa.ForeignKey("ads.id")),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id")),
        sa.Column("assignment_code", sa.String(length=64)),
        sa.Column("explanation", sa.Text()),
        sa.Column("score_breakdown", sa.Text()),
    )
    op.create_index(
        "ix_partner_ad_request_partner",
        "partner_ad_request_events",
        ["partner_id"],
    )

    op.create_table(
        "partner_ad_exposures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("partner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("ad_id", sa.Integer(), sa.ForeignKey("ads.id"), nullable=False),
        sa.Column("last_served_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("partner_id", "ad_id", name="uq_partner_ad_exposure"),
    )
    op.create_index(
        "ix_partner_ad_exposure_partner",
        "partner_ad_exposures",
        ["partner_id"],
    )


def downgrade():
    op.drop_index("ix_partner_ad_exposure_partner", table_name="partner_ad_exposures")
    op.drop_table("partner_ad_exposures")
    op.drop_index("ix_partner_ad_request_partner", table_name="partner_ad_request_events")
    op.drop_table("partner_ad_request_events")
