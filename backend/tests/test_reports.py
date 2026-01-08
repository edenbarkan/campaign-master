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


@pytest.fixture
def client(app):
    return app.test_client()


def test_advertiser_totals_report(app, client):
    with app.app_context():
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

        adv_wallet = Wallet(user_id=advertiser.id, balance_micro=2_000_000, reserved_micro=0)
        pub_wallet = Wallet(user_id=publisher.id, balance_micro=0, reserved_micro=0)

        campaign = Campaign(
            user_id=advertiser.id,
            name='Report Campaign',
            status='active',
            bid_cpm_micro=1_500_000,
            bid_cpc_micro=800_000,
        )
        ad = Ad(
            campaign=campaign,
            title='Report Ad',
            image_url='https://example.com/ad.png',
            landing_url='https://example.com',
            status='active',
        )
        site = Site(
            user_id=publisher.id,
            name='Report Site',
            domain='report.example.com',
        )
        slot = Slot(
            site=site,
            name='Report Slot',
            width=300,
            height=250,
            floor_cpm_micro=900_000,
            floor_cpc_micro=600_000,
            status='active',
        )
        db.session.add_all([adv_wallet, pub_wallet, campaign, ad, site, slot])
        db.session.commit()

        ad_request = AdRequest(
            advertiser_id=advertiser.id,
            publisher_id=publisher.id,
            campaign_id=campaign.id,
            ad_id=ad.id,
            slot_id=slot.id,
            price_cpm_micro=slot.floor_cpm_micro,
            price_cpc_micro=slot.floor_cpc_micro,
            reserved_impression_micro=900,
            reserved_click_micro=600_000,
            reserved_until=datetime.now(timezone.utc),
            status='active',
        )
        db.session.add(ad_request)
        db.session.commit()

        impression = Impression(ad_request_id=ad_request.id, price_micro=900)
        click = Click(ad_request_id=ad_request.id, price_micro=600_000)
        db.session.add_all([impression, click])

        spend_entries = [
            LedgerEntry(
                user_id=advertiser.id,
                entry_type='spend',
                amount_micro=900,
                ref_type='impression',
                ref_id=ad_request.id,
            ),
            LedgerEntry(
                user_id=advertiser.id,
                entry_type='spend',
                amount_micro=600_000,
                ref_type='click',
                ref_id=ad_request.id,
            ),
        ]
        db.session.add_all(spend_entries)
        db.session.commit()

    login_resp = client.post('/api/auth/login', json={
        'email': 'adv@example.com',
        'password': 'password123',
    })
    assert login_resp.status_code == 200

    report_resp = client.get('/api/reports/advertiser')
    assert report_resp.status_code == 200
    data = report_resp.get_json()
    assert data['totals']['impressions'] == 1
    assert data['totals']['clicks'] == 1
    assert data['totals']['spend_micro'] == 600_900


def test_publisher_totals_report(app, client):
    with app.app_context():
        advertiser = User(
            email='advpub@example.com',
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

        adv_wallet = Wallet(user_id=advertiser.id, balance_micro=2_000_000, reserved_micro=0)
        pub_wallet = Wallet(user_id=publisher.id, balance_micro=0, reserved_micro=0)

        campaign = Campaign(
            user_id=advertiser.id,
            name='Publisher Campaign',
            status='active',
            bid_cpm_micro=1_500_000,
            bid_cpc_micro=800_000,
        )
        ad = Ad(
            campaign=campaign,
            title='Publisher Ad',
            image_url='https://example.com/ad.png',
            landing_url='https://example.com',
            status='active',
        )
        site = Site(
            user_id=publisher.id,
            name='Publisher Site',
            domain='publisher.example.com',
        )
        slot = Slot(
            site=site,
            name='Publisher Slot',
            width=300,
            height=250,
            floor_cpm_micro=900_000,
            floor_cpc_micro=600_000,
            status='active',
        )
        db.session.add_all([adv_wallet, pub_wallet, campaign, ad, site, slot])
        db.session.commit()

        ad_request = AdRequest(
            advertiser_id=advertiser.id,
            publisher_id=publisher.id,
            campaign_id=campaign.id,
            ad_id=ad.id,
            slot_id=slot.id,
            price_cpm_micro=slot.floor_cpm_micro,
            price_cpc_micro=slot.floor_cpc_micro,
            reserved_impression_micro=900,
            reserved_click_micro=600_000,
            reserved_until=datetime.now(timezone.utc),
            status='active',
        )
        db.session.add(ad_request)
        db.session.commit()

        impression = Impression(ad_request_id=ad_request.id, price_micro=900)
        click = Click(ad_request_id=ad_request.id, price_micro=600_000)
        db.session.add_all([impression, click])

        earn_entries = [
            LedgerEntry(
                user_id=publisher.id,
                entry_type='earn',
                amount_micro=900,
                ref_type='impression',
                ref_id=ad_request.id,
            ),
            LedgerEntry(
                user_id=publisher.id,
                entry_type='earn',
                amount_micro=600_000,
                ref_type='click',
                ref_id=ad_request.id,
            ),
        ]
        db.session.add_all(earn_entries)
        db.session.commit()

    login_resp = client.post('/api/auth/login', json={
        'email': 'publisher@example.com',
        'password': 'password123',
    })
    assert login_resp.status_code == 200

    report_resp = client.get('/api/reports/publisher')
    assert report_resp.status_code == 200
    data = report_resp.get_json()
    assert data['totals']['impressions'] == 1
    assert data['totals']['clicks'] == 1
    assert data['totals']['earn_micro'] == 600_900


def test_reports_reflect_tracking_flow(app):
    reserved_impression = 900
    reserved_click = 600_000

    with app.app_context():
        advertiser = User(
            email='flowadv@example.com',
            is_advertiser=True,
            is_publisher=False,
        )
        advertiser.set_password('password123')
        publisher = User(
            email='flowpub@example.com',
            is_advertiser=False,
            is_publisher=True,
        )
        publisher.set_password('password123')
        db.session.add_all([advertiser, publisher])
        db.session.commit()

        adv_wallet = Wallet(
            user_id=advertiser.id,
            balance_micro=2_000_000,
            reserved_micro=reserved_impression + reserved_click,
        )
        pub_wallet = Wallet(user_id=publisher.id, balance_micro=0, reserved_micro=0)

        site = Site(
            user_id=publisher.id,
            name='Flow Site',
            domain='flow.example.com',
        )
        slot = Slot(
            site=site,
            name='Flow Slot',
            width=300,
            height=250,
            floor_cpm_micro=900_000,
            floor_cpc_micro=600_000,
            status='active',
        )
        campaign = Campaign(
            user_id=advertiser.id,
            name='Flow Campaign',
            status='active',
            bid_cpm_micro=1_500_000,
            bid_cpc_micro=800_000,
        )
        ad = Ad(
            campaign=campaign,
            title='Flow Ad',
            image_url='https://example.com/flow.png',
            landing_url='https://example.com',
            status='active',
        )

        db.session.add_all([adv_wallet, pub_wallet, site, slot, campaign, ad])
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
        db.session.commit()

        request_id = ad_request.request_id

    client = app.test_client()

    imp_resp = client.get(f'/api/track/impression?request_id={request_id}')
    assert imp_resp.status_code == 204
    click_resp = client.get(f'/api/track/click?request_id={request_id}')
    assert click_resp.status_code == 302

    session_client = app.test_client()

    assert session_client.post('/api/auth/login', json={
        'email': 'flowadv@example.com',
        'password': 'password123',
    }).status_code == 200

    adv_report_resp = session_client.get('/api/reports/advertiser')
    assert adv_report_resp.status_code == 200, adv_report_resp.get_json()
    adv_report = adv_report_resp.get_json()['totals']

    assert session_client.post('/api/auth/logout').status_code == 200
    assert session_client.post('/api/auth/login', json={
        'email': 'flowpub@example.com',
        'password': 'password123',
    }).status_code == 200

    pub_report_resp = session_client.get('/api/reports/publisher')
    assert pub_report_resp.status_code == 200, pub_report_resp.get_json()
    pub_report = pub_report_resp.get_json()['totals']

    assert adv_report['impressions'] == 1
    assert adv_report['clicks'] == 1
    assert adv_report['spend_micro'] == reserved_impression + reserved_click

    assert pub_report['impressions'] == 1
    assert pub_report['clicks'] == 1
    assert pub_report['earn_micro'] == reserved_impression + reserved_click


def test_advertiser_report_uses_campaign_owner(app, client):
    with app.app_context():
        advertiser = User(
            email='owner@example.com',
            is_advertiser=True,
            is_publisher=False,
        )
        advertiser.set_password('password123')
        publisher = User(
            email='ownerpub@example.com',
            is_advertiser=False,
            is_publisher=True,
        )
        publisher.set_password('password123')
        db.session.add_all([advertiser, publisher])
        db.session.commit()

        campaign = Campaign(
            user_id=advertiser.id,
            name='Owner Campaign',
            status='active',
            bid_cpm_micro=1_500_000,
            bid_cpc_micro=800_000,
        )
        ad = Ad(
            campaign=campaign,
            title='Owner Ad',
            image_url='https://example.com/owner.png',
            landing_url='https://example.com',
            status='active',
        )
        site = Site(
            user_id=publisher.id,
            name='Owner Site',
            domain='owner.example.com',
        )
        slot = Slot(
            site=site,
            name='Owner Slot',
            width=300,
            height=250,
            floor_cpm_micro=900_000,
            floor_cpc_micro=600_000,
            status='active',
        )
        db.session.add_all([campaign, ad, site, slot])
        db.session.commit()

        ad_request = AdRequest(
            advertiser_id=publisher.id,  # intentionally wrong to simulate legacy data
            publisher_id=publisher.id,
            campaign_id=campaign.id,
            ad_id=ad.id,
            slot_id=slot.id,
            price_cpm_micro=slot.floor_cpm_micro,
            price_cpc_micro=slot.floor_cpc_micro,
            reserved_impression_micro=900,
            reserved_click_micro=600_000,
            reserved_until=datetime.now(timezone.utc),
            status='active',
        )
        db.session.add(ad_request)
        db.session.commit()

        db.session.add_all([
            Impression(ad_request_id=ad_request.id, price_micro=900),
            Click(ad_request_id=ad_request.id, price_micro=600_000),
            LedgerEntry(
                user_id=advertiser.id,
                entry_type='spend',
                amount_micro=900,
                ref_type='impression',
                ref_id=ad_request.id,
            ),
            LedgerEntry(
                user_id=advertiser.id,
                entry_type='spend',
                amount_micro=600_000,
                ref_type='click',
                ref_id=ad_request.id,
            ),
        ])
        db.session.commit()

    login_resp = client.post('/api/auth/login', json={
        'email': 'owner@example.com',
        'password': 'password123',
    })
    assert login_resp.status_code == 200

    report_resp = client.get('/api/reports/advertiser')
    assert report_resp.status_code == 200
    data = report_resp.get_json()
    assert data['totals']['impressions'] == 1
    assert data['totals']['clicks'] == 1
    assert data['totals']['spend_micro'] == 600_900


def test_advertiser_report_forbidden_for_publisher(app, client):
    with app.app_context():
        publisher = User(
            email='onlypub@example.com',
            is_advertiser=False,
            is_publisher=True,
        )
        publisher.set_password('password123')
        db.session.add(publisher)
        db.session.commit()

    login_resp = client.post('/api/auth/login', json={
        'email': 'onlypub@example.com',
        'password': 'password123',
    })
    assert login_resp.status_code == 200

    report_resp = client.get('/api/reports/advertiser')
    assert report_resp.status_code == 403
    assert report_resp.get_json()['error'] == 'Forbidden'


def test_publisher_report_forbidden_for_advertiser(app, client):
    with app.app_context():
        advertiser = User(
            email='onlyadv@example.com',
            is_advertiser=True,
            is_publisher=False,
        )
        advertiser.set_password('password123')
        db.session.add(advertiser)
        db.session.commit()

    login_resp = client.post('/api/auth/login', json={
        'email': 'onlyadv@example.com',
        'password': 'password123',
    })
    assert login_resp.status_code == 200

    report_resp = client.get('/api/reports/publisher')
    assert report_resp.status_code == 403
    assert report_resp.get_json()['error'] == 'Forbidden'
