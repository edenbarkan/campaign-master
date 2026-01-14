import os
import sys
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pytest

from app import create_app
from app.extensions import db
from app.models.ad import Ad
from app.models.assignment import AdAssignment
from app.models.campaign import Campaign
from app.models.tracking_event import TrackingEvent
from app.models.user import User
from app.services.pricing import compute_partner_payout


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "JWT_SECRET_KEY": "test-secret",
            "PLATFORM_FEE_PERCENT": "30",
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_auth_flow(client):
    register = client.post(
        "/api/auth/register",
        json={
            "email": "buyer-test@example.com",
            "password": "secret",
            "role": "buyer",
        },
    )
    assert register.status_code == 201
    assert register.get_json()["user"]["role"] == "BUYER"

    login = client.post(
        "/api/auth/login",
        json={"email": "buyer-test@example.com", "password": "secret"},
    )
    assert login.status_code == 200
    token = login.get_json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.get_json()["user"]["email"] == "buyer-test@example.com"
    assert me.get_json()["user"]["role"] == "BUYER"


def test_tracking_click_redirect(client, app):
    with app.app_context():
        buyer = User(email="buyer@example.com", role="buyer")
        buyer.set_password("pass")
        partner = User(email="partner@example.com", role="partner")
        partner.set_password("pass")
        db.session.add_all([buyer, partner])
        db.session.commit()

        campaign = Campaign(
            buyer_id=buyer.id,
            name="Sample",
            status="active",
            budget_total=Decimal("100.00"),
            budget_spent=Decimal("0.00"),
            buyer_cpc=Decimal("2.50"),
            partner_payout=Decimal("1.25"),
        )
        db.session.add(campaign)
        db.session.commit()
        campaign_id = campaign.id

        ad = Ad(
            campaign_id=campaign.id,
            title="Sprint",
            body="Fast shoes",
            image_url="https://example.com/ad.png",
            destination_url="https://example.com/landing",
            active=True,
        )
        db.session.add(ad)
        db.session.commit()

        assignment = AdAssignment(
            code="testcode",
            partner_id=partner.id,
            campaign_id=campaign.id,
            ad_id=ad.id,
        )
        db.session.add(assignment)
        db.session.commit()

    response = client.get("/t/testcode")
    assert response.status_code == 302
    assert response.headers["Location"] == "https://example.com/landing"

    with app.app_context():
        click_count = TrackingEvent.query.filter_by(event_type="click").count()
        assert click_count == 1
        refreshed_campaign = Campaign.query.get(campaign_id)
        assert float(refreshed_campaign.budget_spent) == 2.5


def test_campaign_pricing_computed(client):
    register = client.post(
        "/api/auth/register",
        json={
            "email": "pricing@example.com",
            "password": "secret",
            "role": "buyer",
        },
    )
    assert register.status_code == 201
    token = register.get_json()["access_token"]

    create_response = client.post(
        "/api/buyer/campaigns",
        json={
            "name": "Pricing Test",
            "status": "active",
            "budget_total": 500,
            "max_cpc": 10,
            "partner_payout": 9,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_response.status_code == 201
    campaign = create_response.get_json()["campaign"]
    assert campaign["max_cpc"] == 10.0
    assert campaign["partner_payout"] == 7.0
    assert campaign["platform_fee_percent"] == 30.0

    update_response = client.put(
        f"/api/buyer/campaigns/{campaign['id']}",
        json={"max_cpc": 4, "partner_payout": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_response.status_code == 200
    updated = update_response.get_json()["campaign"]
    assert updated["max_cpc"] == 4.0
    assert updated["partner_payout"] == 2.8


def test_pricing_formula_values(app):
    with app.app_context():
        app.config["PLATFORM_FEE_PERCENT"] = "30"
        assert float(compute_partner_payout(Decimal("1.00"))) == 0.7
        assert float(compute_partner_payout(Decimal("2.50"))) == 1.75
        app.config["PLATFORM_FEE_PERCENT"] = "15"
        assert float(compute_partner_payout(Decimal("1.00"))) == 0.85


def test_click_tracking_updates_earnings(client, app):
    with app.app_context():
        buyer = User(email="buyer-earnings@example.com", role="buyer")
        buyer.set_password("pass")
        partner = User(email="partner-earnings@example.com", role="partner")
        partner.set_password("pass")
        db.session.add_all([buyer, partner])
        db.session.commit()

        expected_payout = compute_partner_payout(Decimal("10.00"))
        campaign = Campaign(
            buyer_id=buyer.id,
            name="Earnings Test",
            status="active",
            budget_total=Decimal("100.00"),
            budget_spent=Decimal("0.00"),
            buyer_cpc=Decimal("10.00"),
            partner_payout=expected_payout,
        )
        db.session.add(campaign)
        db.session.commit()
        campaign_id = campaign.id

        ad = Ad(
            campaign_id=campaign.id,
            title="Earnings Ad",
            body="Test body",
            image_url="https://example.com/ad.png",
            destination_url="https://example.com/landing",
            active=True,
        )
        db.session.add(ad)
        db.session.commit()

        assignment = AdAssignment(
            code="earningscode",
            partner_id=partner.id,
            campaign_id=campaign.id,
            ad_id=ad.id,
        )
        db.session.add(assignment)
        db.session.commit()

    click_response = client.get("/t/earningscode")
    assert click_response.status_code == 302

    login = client.post(
        "/api/auth/login",
        json={"email": "partner-earnings@example.com", "password": "pass"},
    )
    assert login.status_code == 200
    token = login.get_json()["access_token"]

    analytics = client.get(
        "/api/partner/analytics/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert analytics.status_code == 200
    totals = analytics.get_json()["totals"]
    assert totals["earnings"] == float(expected_payout)
    assert totals["clicks"] == 1

    with app.app_context():
        refreshed_campaign = Campaign.query.get(campaign_id)
        assert float(refreshed_campaign.budget_spent) == 10.0
