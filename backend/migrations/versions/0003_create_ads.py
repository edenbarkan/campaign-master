"""create ads

Revision ID: 0003_create_ads
Revises: 0002_create_campaigns
Create Date: 2026-01-13 12:50:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "0003_create_ads"
down_revision = "0002_create_campaigns"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("destination_url", sa.String(length=500), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_ads_campaign_id"), "ads", ["campaign_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_ads_campaign_id"), table_name="ads")
    op.drop_table("ads")
