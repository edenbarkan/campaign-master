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
from app.models.click_event import ClickEvent
from app.models.impression_event import ImpressionEvent
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
            "CLICK_HASH_SALT": "testsalt",
            "CLICK_DUPLICATE_WINDOW_SECONDS": 10,
            "CLICK_RATE_LIMIT_PER_MINUTE": 20,
            "IMPRESSION_DEDUP_WINDOW_SECONDS": 60,
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def create_users():
    buyer = User(email="buyer@example.com", role="buyer")
    buyer.set_password("pass")
    partner = User(email="partner@example.com", role="partner")
    partner.set_password("pass")
    admin = User(email="admin@example.com", role="admin")
    admin.set_password("pass")
    db.session.add_all([buyer, partner, admin])
    db.session.commit()
    return buyer, partner, admin


def create_campaign(buyer_id, max_cpc, budget_total):
    partner_payout = compute_partner_payout(Decimal(max_cpc))
    campaign = Campaign(
        buyer_id=buyer_id,
        name="Sample",
        status="active",
        budget_total=Decimal(budget_total),
        budget_spent=Decimal("0.00"),
        buyer_cpc=Decimal(max_cpc),
        partner_payout=partner_payout,
    )
    db.session.add(campaign)
    db.session.commit()
    return campaign


def create_ad(campaign_id):
    ad = Ad(
        campaign_id=campaign_id,
        title="Sprint",
        body="Fast shoes",
        image_url="https://example.com/ad.png",
        destination_url="https://example.com/landing",
        active=True,
    )
    db.session.add(ad)
    db.session.commit()
    return ad


def create_assignment(code, partner_id, campaign_id, ad_id):
    assignment = AdAssignment(
        code=code,
        partner_id=partner_id,
        campaign_id=campaign_id,
        ad_id=ad_id,
    )
    db.session.add(assignment)
    db.session.commit()
    return assignment


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
        buyer, partner, _ = create_users()
        campaign = create_campaign(buyer.id, "2.50", "100.00")
        ad = create_ad(campaign.id)
        create_assignment("testcode", partner.id, campaign.id, ad.id)

    response = client.get(
        "/t/testcode",
        headers={"User-Agent": "pytest", "X-Forwarded-For": "10.0.0.1"},
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "https://example.com/landing"

    with app.app_context():
        click_count = ClickEvent.query.filter_by(status="ACCEPTED").count()
        assert click_count == 1
        refreshed_campaign = Campaign.query.first()
        assert float(refreshed_campaign.budget_spent) == 2.5


def test_duplicate_click_rejected_no_economics(client, app):
    with app.app_context():
        buyer, partner, _ = create_users()
        campaign = create_campaign(buyer.id, "2.50", "100.00")
        ad = create_ad(campaign.id)
        create_assignment("dupcode", partner.id, campaign.id, ad.id)

    headers = {"User-Agent": "pytest", "X-Forwarded-For": "10.0.0.2"}
    first = client.get("/t/dupcode", headers=headers)
    assert first.status_code == 302
    second = client.get("/t/dupcode", headers=headers)
    assert second.status_code == 302

    with app.app_context():
        clicks = ClickEvent.query.filter_by(assignment_code="dupcode").all()
        assert len(clicks) == 2
        accepted = [c for c in clicks if c.status == "ACCEPTED"]
        rejected = [c for c in clicks if c.status == "REJECTED"]
        assert len(accepted) == 1
        assert len(rejected) == 1
        assert rejected[0].reject_reason == "DUPLICATE_CLICK"
        campaign = Campaign.query.first()
        assert float(campaign.budget_spent) == 2.5
        earnings = (
            db.session.query(db.func.sum(ClickEvent.earnings_delta))
            .filter(ClickEvent.status == "ACCEPTED")
            .scalar()
            or 0
        )
        assert float(earnings) == float(campaign.partner_payout)


def test_budget_exhausted_pauses_campaign(client, app):
    with app.app_context():
        buyer, partner, _ = create_users()
        campaign = create_campaign(buyer.id, "2.50", "1.00")
        ad = create_ad(campaign.id)
        create_assignment("budgetcode", partner.id, campaign.id, ad.id)

    response = client.get(
        "/t/budgetcode",
        headers={"User-Agent": "pytest", "X-Forwarded-For": "10.0.0.3"},
    )
    assert response.status_code == 302

    with app.app_context():
        click = ClickEvent.query.filter_by(assignment_code="budgetcode").first()
        assert click.status == "REJECTED"
        assert click.reject_reason == "BUDGET_EXHAUSTED"
        campaign = Campaign.query.first()
        assert campaign.status == "paused"
        assert float(campaign.budget_spent) == 0.0


def test_impression_dedup(client, app):
    with app.app_context():
        buyer, partner, _ = create_users()
        campaign = create_campaign(buyer.id, "2.50", "100.00")
        ad = create_ad(campaign.id)
        create_assignment("impressioncode", partner.id, campaign.id, ad.id)

    headers = {"User-Agent": "pytest", "X-Forwarded-For": "10.0.0.4"}
    first = client.post("/api/track/impression?code=impressioncode", headers=headers)
    assert first.status_code == 200
    second = client.post("/api/track/impression?code=impressioncode", headers=headers)
    assert second.status_code == 200

    with app.app_context():
        impressions = ImpressionEvent.query.filter_by(assignment_code="impressioncode").all()
        assert len(impressions) == 2
        statuses = {impression.status for impression in impressions}
        assert "ACCEPTED" in statuses
        assert "DEDUPED" in statuses


def test_admin_risk_requires_admin(client, app):
    with app.app_context():
        buyer, _, admin = create_users()
        buyer_email = buyer.email
        admin_email = admin.email

    login = client.post(
        "/api/auth/login",
        json={"email": buyer_email, "password": "pass"},
    )
    assert login.status_code == 200
    token = login.get_json()["access_token"]

    denied = client.get(
        "/api/admin/risk/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert denied.status_code == 403

    admin_login = client.post(
        "/api/auth/login",
        json={"email": admin_email, "password": "pass"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.get_json()["access_token"]

    allowed = client.get(
        "/api/admin/risk/summary",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert allowed.status_code == 200


def test_partner_quality_requires_partner(client, app):
    with app.app_context():
        buyer, partner, _ = create_users()
        buyer_email = buyer.email
        partner_email = partner.email

    buyer_login = client.post(
        "/api/auth/login",
        json={"email": buyer_email, "password": "pass"},
    )
    assert buyer_login.status_code == 200
    buyer_token = buyer_login.get_json()["access_token"]

    denied = client.get(
        "/api/partner/quality/summary",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert denied.status_code == 403

    partner_login = client.post(
        "/api/auth/login",
        json={"email": partner_email, "password": "pass"},
    )
    assert partner_login.status_code == 200
    partner_token = partner_login.get_json()["access_token"]

    allowed = client.get(
        "/api/partner/quality/summary",
        headers={"Authorization": f"Bearer {partner_token}"},
    )
    assert allowed.status_code == 200


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
        buyer, partner, _ = create_users()
        expected_payout = compute_partner_payout(Decimal("10.00"))
        campaign = create_campaign(buyer.id, "10.00", "100.00")
        ad = create_ad(campaign.id)
        create_assignment("earningscode", partner.id, campaign.id, ad.id)

    click_response = client.get(
        "/t/earningscode",
        headers={"User-Agent": "pytest", "X-Forwarded-For": "10.0.0.5"},
    )
    assert click_response.status_code == 302

    login = client.post(
        "/api/auth/login",
        json={"email": "partner@example.com", "password": "pass"},
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
        refreshed_campaign = Campaign.query.first()
        assert float(refreshed_campaign.budget_spent) == 10.0
