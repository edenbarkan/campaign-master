from datetime import datetime, timedelta, timezone

import pytest

from app import create_app, db
from app.adserver.service import release_expired_reservations
from app.models import (
    Ad,
    AdRequest,
    Campaign,
    Site,
    Slot,
    User,
    Wallet,
)


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def test_release_expired_reservations(app):
    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(minutes=5)

    with app.app_context():
        advertiser = User(
            email='advertiser@example.com',
            is_advertiser=True,
            is_publisher=False,
        )
        advertiser.set_password('password123')
        publisher = User(
            email='publisher@example.com',
            is_advertiser=False,
            is_publisher=True,
        )
        publisher.set_password('password123')
        db.session.add_all([advertiser, publisher])
        db.session.commit()

        wallet = Wallet(
            user_id=advertiser.id,
            balance_micro=2_000_000,
            reserved_micro=0,
        )

        campaign = Campaign(
            user_id=advertiser.id,
            name='Test campaign',
            status='active',
        )
        ad = Ad(
            campaign=campaign,
            title='Test ad',
            image_url='https://example.com/ad.png',
            landing_url='https://example.com',
            status='active',
        )
        site = Site(
            user_id=publisher.id,
            name='Publisher site',
            domain='example.com',
        )
        slot = Slot(
            site=site,
            name='Sidebar',
            width=300,
            height=250,
            status='active',
        )

        db.session.add_all([wallet, campaign, ad, site, slot])
        db.session.commit()

        ad_request = AdRequest(
            advertiser_id=advertiser.id,
            publisher_id=publisher.id,
            campaign_id=campaign.id,
            ad_id=ad.id,
            slot_id=slot.id,
            price_cpm_micro=1500000,
            price_cpc_micro=500000,
            reserved_impression_micro=400000,
            reserved_click_micro=200000,
            reserved_until=expired_time,
            impression_tracked_at=None,
            click_tracked_at=None,
            status='active',
        )

        wallet.reserved_micro = (
            ad_request.reserved_impression_micro + ad_request.reserved_click_micro
        )

        db.session.add(ad_request)
        db.session.commit()

        release_expired_reservations(db.session, now=now)

        # Wallet reserved micro should be cleared after release.
        refreshed_wallet = Wallet.query.filter_by(user_id=advertiser.id).one()
        assert refreshed_wallet.reserved_micro == 0

        refreshed_request = AdRequest.query.filter_by(id=ad_request.id).one()
        assert refreshed_request.status == 'expired'

        # Calling again should be a no-op (idempotent behavior).
        release_expired_reservations(db.session, now=now)
        assert db.session.get(Wallet, wallet.id).reserved_micro == 0
        assert db.session.get(AdRequest, ad_request.id).status == 'expired'
