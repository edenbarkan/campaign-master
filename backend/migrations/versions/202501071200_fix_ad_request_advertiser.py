"""Backfill ad_request advertiser_id from campaign owner."""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '202501071200'
down_revision = 'b64f89d9fbbb'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE ad_request
        SET advertiser_id = campaign.user_id
        FROM campaign
        WHERE ad_request.campaign_id = campaign.id
    """))


def downgrade():
    # irreversible
    pass
