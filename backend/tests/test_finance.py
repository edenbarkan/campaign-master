from datetime import datetime, timedelta, timezone

import pytest

from app import create_app, db
from app.models import (
    Ad,
    AdRequest,
    Campaign,
    LedgerEntry,
    Site,
    Slot,
    User,
    Wallet,
)


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _seed_basic_entities():
    advertiser = User(
        email='adv@example.com',
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

    campaign = Campaign(
        user_id=advertiser.id,
        name='Test Campaign',
        status='active',
        bid_cpm_micro=1_500_000,
        bid_cpc_micro=800_000,
    )
    ad = Ad(
        campaign=campaign,
        title='Test Ad',
        image_url='https://example.com/ad.png',
        landing_url='https://example.com',
        status='active',
    )
    site = Site(
        user_id=publisher.id,
        name='Test Site',
        domain='test.example.com',
    )
    slot = Slot(
        site=site,
        name='Test Slot',
        width=300,
        height=250,
        floor_cpm_micro=900_000,
        floor_cpc_micro=600_000,
        status='active',
    )
    db.session.add_all([campaign, ad, site, slot])
    db.session.commit()

    return advertiser, publisher, campaign, ad, slot


def test_ad_request_sets_advertiser_id_from_campaign_owner(app):
    with app.app_context():
        advertiser, publisher, campaign, ad, slot = _seed_basic_entities()
        advertiser_id = advertiser.id
        publisher_id = publisher.id

        ad_request = AdRequest(
            request_id='abc',
            advertiser_id=publisher.id,  # intentionally wrong
            publisher_id=publisher.id,
            campaign_id=campaign.id,
            ad_id=ad.id,
            slot_id=slot.id,
            price_cpm_micro=slot.floor_cpm_micro,
            price_cpc_micro=slot.floor_cpc_micro,
            reserved_impression_micro=900,
            reserved_click_micro=600_000,
            reserved_until=datetime.now(timezone.utc) + timedelta(minutes=5),
            status='active',
        )
        db.session.add(ad_request)
        db.session.commit()

        assert ad_request.advertiser_id == advertiser.id


def test_money_conservation_on_click(app, client):
    with app.app_context():
        advertiser, publisher, campaign, ad, slot = _seed_basic_entities()
        advertiser_id = advertiser.id
        publisher_id = publisher.id

        adv_wallet = Wallet(
            user_id=advertiser.id,
            balance_micro=2_000_000,
            reserved_micro=0,
        )
        pub_wallet = Wallet(
            user_id=publisher.id,
            balance_micro=0,
            reserved_micro=0,
        )
        db.session.add_all([adv_wallet, pub_wallet])
        db.session.commit()

        impression_cost = 900
        click_cost = 600_000
        total_cost = impression_cost + click_cost

        adv_wallet.reserved_micro = total_cost
        db.session.add(adv_wallet)

        ad_request = AdRequest(
            request_id='money-check',
            advertiser_id=advertiser.id,
            publisher_id=publisher.id,
            campaign_id=campaign.id,
            ad_id=ad.id,
            slot_id=slot.id,
            price_cpm_micro=slot.floor_cpm_micro,
            price_cpc_micro=slot.floor_cpc_micro,
            reserved_impression_micro=impression_cost,
            reserved_click_micro=click_cost,
            reserved_until=datetime.now(timezone.utc) + timedelta(minutes=5),
            status='active',
        )
        db.session.add(ad_request)
        db.session.commit()

    resp = client.get('/api/track/impression?request_id=money-check')
    assert resp.status_code == 204
    resp = client.get('/api/track/click?request_id=money-check')
    assert resp.status_code == 302

    with app.app_context():
        adv_wallet = Wallet.query.filter_by(user_id=advertiser_id).one()
        pub_wallet = Wallet.query.filter_by(user_id=publisher_id).one()
        assert adv_wallet.balance_micro == 2_000_000 - total_cost
        assert adv_wallet.reserved_micro == 0
        assert pub_wallet.balance_micro == total_cost

        adv_spend = sum(
            entry.amount_micro
            for entry in LedgerEntry.query.filter_by(
                user_id=advertiser_id, entry_type='spend'
            )
        )
        pub_earn = sum(
            entry.amount_micro
            for entry in LedgerEntry.query.filter_by(
                user_id=publisher_id, entry_type='earn'
            )
        )
        assert adv_spend == pub_earn == total_cost
