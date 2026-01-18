import os
import sys
from datetime import datetime
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pytest

from app import create_app
from app.extensions import db
from app.models.ad import Ad
from app.models.campaign import Campaign
from app.models.click_event import ClickEvent
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
            "FREQ_CAP_SECONDS": 0,
            "MATCH_REJECT_LOOKBACK_DAYS": 7,
            "MATCH_REJECT_PENALTY_WEIGHT": 2.0,
            "MATCHING_DEBUG": "1",
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def create_user(email, role, password="pass"):
    user = User(email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def create_campaign(buyer_id, name):
    partner_payout = compute_partner_payout(Decimal("2.00"))
    campaign = Campaign(
        buyer_id=buyer_id,
        name=name,
        status="active",
        budget_total=Decimal("100.00"),
        budget_spent=Decimal("0.00"),
        buyer_cpc=Decimal("2.00"),
        partner_payout=partner_payout,
    )
    db.session.add(campaign)
    db.session.commit()
    return campaign


def create_ad(campaign_id, title):
    ad = Ad(
        campaign_id=campaign_id,
        title=title,
        body="Ad body",
        image_url="https://example.com/ad.png",
        destination_url="https://example.com/landing",
        active=True,
    )
    db.session.add(ad)
    db.session.commit()
    return ad


def login_partner(client, email):
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "pass"},
    )
    assert response.status_code == 200
    return response.get_json()["access_token"]


def test_reject_penalty_same_across_candidates(client, app):
    with app.app_context():
        buyer = create_user("buyer@example.com", "buyer")
        partner = create_user("partner@example.com", "partner")
        campaign_a = create_campaign(buyer.id, "Campaign A")
        campaign_b = create_campaign(buyer.id, "Campaign B")
        create_ad(campaign_a.id, "Ad A")
        create_ad(campaign_b.id, "Ad B")

    token = login_partner(client, "partner@example.com")

    response = client.get(
        "/api/partner/ad",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    candidates = payload.get("debug_candidates")
    assert candidates is not None
    assert len(candidates) >= 2

    penalties = {
        candidate["score_breakdown"]["partner_reject_penalty"] for candidate in candidates
    }
    rates = {
        candidate["score_breakdown"]["partner_reject_rate"] for candidate in candidates
    }
    weights = {
        candidate["score_breakdown"]["partner_reject_penalty_weight"]
        for candidate in candidates
    }

    assert len(penalties) == 1
    assert len(rates) == 1
    assert len(weights) == 1

    rate = rates.pop()
    weight = weights.pop()
    penalty = penalties.pop()
    assert penalty == pytest.approx(round(rate * weight, 4))


def test_reject_penalty_changes_after_rejection(client, app):
    with app.app_context():
        buyer = create_user("buyer2@example.com", "buyer")
        partner = create_user("partner2@example.com", "partner")
        campaign = create_campaign(buyer.id, "Campaign C")
        ad = create_ad(campaign.id, "Ad C")
        partner_id = partner.id
        ad_id = ad.id
        campaign_id = campaign.id

    token = login_partner(client, "partner2@example.com")

    initial = client.get(
        "/api/partner/ad",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert initial.status_code == 200
    initial_breakdown = initial.get_json()["score_breakdown"]
    assert initial_breakdown["partner_reject_rate"] == 0
    assert initial_breakdown["partner_reject_penalty"] == 0

    with app.app_context():
        db.session.add(
            ClickEvent(
                assignment_code="reject-test",
                partner_id=partner_id,
                campaign_id=campaign_id,
                ad_id=ad_id,
                ip_hash="hash",
                ua_hash="ua",
                status="REJECTED",
                reject_reason="DUPLICATE_CLICK",
                ts=datetime.utcnow(),
                spend_delta=Decimal("0"),
                earnings_delta=Decimal("0"),
                profit_delta=Decimal("0"),
            )
        )
        db.session.commit()

    after = client.get(
        "/api/partner/ad",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert after.status_code == 200
    after_breakdown = after.get_json()["score_breakdown"]

    rate = after_breakdown["partner_reject_rate"]
    penalty = after_breakdown["partner_reject_penalty"]
    weight = after_breakdown["partner_reject_penalty_weight"]

    assert rate == pytest.approx(1.0)
    assert penalty == pytest.approx(round(rate * weight, 4))
    assert penalty > initial_breakdown["partner_reject_penalty"]
