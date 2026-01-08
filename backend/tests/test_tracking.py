import os
from datetime import datetime, timedelta, timezone

import pytest

from app import create_app, db
from app.models import (
    Ad,
    AdRequest,
    Campaign,
    Click,
    Impression,
    LedgerEntry,
    Site,
    Slot,
    User,
    Wallet,
)


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


def test_impression_tracking_idempotent(app):
    reserved_impression = 400_000
    reserved_click = 200_000

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

        advertiser_wallet = Wallet(
            user_id=advertiser.id,
            balance_micro=2_000_000,
            reserved_micro=0,
        )
        publisher_wallet = Wallet(
            user_id=publisher.id,
            balance_micro=0,
            reserved_micro=0,
        )

        site = Site(
            user_id=publisher.id,
            name='Publisher Site',
            domain='example.com',
        )
        slot = Slot(
            site=site,
            name='Sidebar',
            width=300,
            height=250,
            floor_cpm_micro=900_000,
            floor_cpc_micro=400_000,
            status='active',
        )

        campaign = Campaign(
            user_id=advertiser.id,
            name='Spring Campaign',
            status='active',
            bid_cpm_micro=1_200_000,
            bid_cpc_micro=500_000,
        )
        ad = Ad(
            campaign=campaign,
            title='Ad Title',
            image_url='https://example.com/ad.jpg',
            landing_url='https://example.com',
            status='active',
        )

        db.session.add_all([
            advertiser_wallet,
            publisher_wallet,
            site,
            slot,
            campaign,
            ad,
        ])
        db.session.commit()

        ad_request = AdRequest(
            advertiser_id=advertiser.id,
            publisher_id=publisher.id,
            campaign_id=campaign.id,
            ad_id=ad.id,
            slot_id=slot.id,
            price_cpm_micro=slot.floor_cpm_micro,
            price_cpc_micro=slot.floor_cpc_micro,
            reserved_impression_micro=reserved_impression,
            reserved_click_micro=reserved_click,
            reserved_until=datetime.now(timezone.utc) + timedelta(minutes=5),
            status='active',
        )
        db.session.add(ad_request)
        advertiser_wallet.reserved_micro = reserved_impression + reserved_click
        db.session.commit()

        request_id = ad_request.request_id
        advertiser_id = advertiser.id
        publisher_id = publisher.id
        ad_request_id = ad_request.id

    client = app.test_client()

    first_response = client.get(f'/api/track/impression?request_id={request_id}')
    assert first_response.status_code == 204

    with app.app_context():
        adv_wallet = Wallet.query.filter_by(user_id=advertiser_id).one()
        pub_wallet = Wallet.query.filter_by(user_id=publisher_id).one()
        assert adv_wallet.reserved_micro == reserved_click
        assert adv_wallet.balance_micro == 2_000_000 - reserved_impression
        assert pub_wallet.balance_micro == reserved_impression

        ad_request = AdRequest.query.get(ad_request_id)
        assert ad_request.impression_tracked_at is not None
        assert ad_request.status == 'active'

        impressions = Impression.query.filter_by(ad_request_id=ad_request_id).all()
        assert len(impressions) == 1
        assert impressions[0].price_micro == reserved_impression

        advertiser_entries = LedgerEntry.query.filter_by(
            user_id=advertiser_id,
            entry_type='spend',
        ).all()
        publisher_entries = LedgerEntry.query.filter_by(
            user_id=publisher_id,
            entry_type='earn',
        ).all()
        assert len(advertiser_entries) == 1
        assert advertiser_entries[0].amount_micro == reserved_impression
        assert len(publisher_entries) == 1
        assert publisher_entries[0].amount_micro == reserved_impression

    second_response = client.get(f'/api/track/impression?request_id={request_id}')
    assert second_response.status_code == 204

    with app.app_context():
        assert Impression.query.filter_by(ad_request_id=ad_request_id).count() == 1
        assert LedgerEntry.query.filter_by(
            user_id=advertiser_id,
            entry_type='spend',
        ).count() == 1
        assert LedgerEntry.query.filter_by(
            user_id=publisher_id,
            entry_type='earn',
        ).count() == 1


def test_click_tracking_idempotent(app):
    reserved_impression = 300_000
    reserved_click = 500_000

    with app.app_context():
        advertiser = User(
            email='clicker@example.com',
            is_advertiser=True,
            is_publisher=False,
        )
        advertiser.set_password('password123')

        publisher = User(
            email='pub@example.com',
            is_advertiser=False,
            is_publisher=True,
        )
        publisher.set_password('password123')

        db.session.add_all([advertiser, publisher])
        db.session.commit()

        advertiser_wallet = Wallet(
            user_id=advertiser.id,
            balance_micro=3_000_000,
            reserved_micro=0,
        )
        publisher_wallet = Wallet(
            user_id=publisher.id,
            balance_micro=0,
            reserved_micro=0,
        )

        site = Site(
            user_id=publisher.id,
            name='Click Site',
            domain='clicks.example.com',
        )
        slot = Slot(
            site=site,
            name='Click Slot',
            width=728,
            height=90,
            floor_cpm_micro=800_000,
            floor_cpc_micro=reserved_click,
            status='active',
        )

        campaign = Campaign(
            user_id=advertiser.id,
            name='Click Campaign',
            status='active',
            bid_cpm_micro=1_500_000,
            bid_cpc_micro=800_000,
        )
        ad = Ad(
            campaign=campaign,
            title='Click Ad',
            image_url='https://example.com/click.jpg',
            landing_url='https://example.com/landing',
            status='active',
        )

        db.session.add_all([
            advertiser_wallet,
            publisher_wallet,
            site,
            slot,
            campaign,
            ad,
        ])
        db.session.commit()

        ad_request = AdRequest(
            advertiser_id=advertiser.id,
            publisher_id=publisher.id,
            campaign_id=campaign.id,
            ad_id=ad.id,
            slot_id=slot.id,
            price_cpm_micro=slot.floor_cpm_micro,
            price_cpc_micro=slot.floor_cpc_micro,
            reserved_impression_micro=reserved_impression,
            reserved_click_micro=reserved_click,
            reserved_until=datetime.now(timezone.utc) + timedelta(minutes=5),
            status='active',
        )
        db.session.add(ad_request)
        advertiser_wallet.reserved_micro = reserved_impression + reserved_click
        db.session.commit()

        request_id = ad_request.request_id
        advertiser_id = advertiser.id
        publisher_id = publisher.id
        ad_request_id = ad_request.id
        landing_url = ad.landing_url
        initial_balance = advertiser_wallet.balance_micro

    client = app.test_client()

    first_response = client.get(f'/api/track/click?request_id={request_id}')
    assert first_response.status_code == 302
    assert first_response.headers['Location'] == landing_url

    with app.app_context():
        adv_wallet = Wallet.query.filter_by(user_id=advertiser_id).one()
        pub_wallet = Wallet.query.filter_by(user_id=publisher_id).one()
        assert adv_wallet.reserved_micro == reserved_impression
        assert adv_wallet.balance_micro == initial_balance - reserved_click
        assert pub_wallet.balance_micro == reserved_click

        ad_request = AdRequest.query.get(ad_request_id)
        assert ad_request.click_tracked_at is not None
        assert ad_request.status == 'active'

        clicks = Click.query.filter_by(ad_request_id=ad_request_id).all()
        assert len(clicks) == 1
        assert clicks[0].price_micro == reserved_click

        advertiser_entries = LedgerEntry.query.filter_by(
            user_id=advertiser_id,
            entry_type='spend',
            ref_type='click',
        ).all()
        publisher_entries = LedgerEntry.query.filter_by(
            user_id=publisher_id,
            entry_type='earn',
            ref_type='click',
        ).all()
        assert len(advertiser_entries) == 1
        assert advertiser_entries[0].amount_micro == reserved_click
        assert len(publisher_entries) == 1
        assert publisher_entries[0].amount_micro == reserved_click

    second_response = client.get(f'/api/track/click?request_id={request_id}')
    assert second_response.status_code == 302
    assert second_response.headers['Location'] == landing_url

    with app.app_context():
        assert Click.query.filter_by(ad_request_id=ad_request_id).count() == 1
        assert LedgerEntry.query.filter_by(
            user_id=advertiser_id,
            entry_type='spend',
            ref_type='click',
        ).count() == 1
        assert LedgerEntry.query.filter_by(
            user_id=publisher_id,
            entry_type='earn',
            ref_type='click',
        ).count() == 1
