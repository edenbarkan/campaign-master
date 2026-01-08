import re

import os
import pytest

from app import create_app, db
from app.models import Ad, AdRequest, Campaign, Site, Slot, User, Wallet


@pytest.fixture
def app():
    db_url = os.getenv('DATABASE_URL', 'sqlite:///:memory:')
    if not db_url:
        db_url = 'sqlite:///:memory:'
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': db_url,
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_adserve_reserves_and_handles_insufficient_balance(app):
    floor_cpm = 900000  # 0.90 per 1k impressions
    floor_cpc = 400000  # 0.40 per click
    required_micro = max(1, floor_cpm // 1000) + floor_cpc

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
        db.session.flush()

        wallet = Wallet(
            user_id=advertiser.id,
            balance_micro=10_000_000,
            reserved_micro=0,
        )

        site = Site(
            user_id=publisher.id,
            name='Publisher Site',
            domain='example.com',
        )
        slot = Slot(
            site=site,
            name='Rectangle',
            width=300,
            height=250,
            floor_cpm_micro=floor_cpm,
            floor_cpc_micro=floor_cpc,
            status='active',
        )

        campaign = Campaign(
            user_id=advertiser.id,
            name='Spring Campaign',
            status='active',
            bid_cpm_micro=1_200_000,
            bid_cpc_micro=500000,
        )
        ad = Ad(
            campaign=campaign,
            title='Ad Title',
            image_url='https://example.com/ad.jpg',
            landing_url='https://example.com',
            status='active',
        )

        db.session.add_all([advertiser, publisher, wallet, site, slot, campaign, ad])
        db.session.commit()

        slot_id = slot.id
        advertiser_id = advertiser.id

    client = app.test_client()
    response = client.get(f'/api/adserve?slot_id={slot_id}')
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert '/api/track/click' in body
    assert '/api/track/impression' in body
    assert re.search(r'request_id=[0-9a-f-]+', body)

    with app.app_context():
        wallet = Wallet.query.filter_by(user_id=advertiser_id).one()
        assert wallet.reserved_micro == required_micro

        ad_requests = AdRequest.query.all()
        assert len(ad_requests) == 1
        assert ad_requests[0].reserved_impression_micro == max(1, floor_cpm // 1000)
        assert ad_requests[0].reserved_click_micro == floor_cpc

        # Reduce wallet so no available funds remain
        wallet.balance_micro = wallet.reserved_micro
        db.session.commit()

    response_no_funds = client.get(f'/api/adserve?slot_id={slot_id}')
    assert response_no_funds.status_code == 204

    with app.app_context():
        # Still only a single reservation request.
        assert AdRequest.query.count() == 1
