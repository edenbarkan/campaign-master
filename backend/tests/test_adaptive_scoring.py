import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pytest

from app import create_app
from app.extensions import db
from app.models.ad import Ad
from app.models.campaign import Campaign
from app.models.click_event import ClickEvent
from app.models.partner_ad_request_event import PartnerAdRequestEvent
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
            "MATCH_CTR_LOOKBACK_DAYS": 14,
            "MATCH_REJECT_LOOKBACK_DAYS": 7,
            "MATCH_CTR_WEIGHT": 1.0,
            "MATCH_TARGETING_BONUS": 1.0,
            "MATCH_REJECT_PENALTY_WEIGHT": 1.0,
            "EXPLORATION_RATE": 0.0,
            "EXPLORATION_BONUS": 0.2,
            "EXPLORATION_NEW_PARTNER_REQUESTS": 5,
            "EXPLORATION_NEW_AD_SERVES": 1,
            "EXPLORATION_MAX_AD_SERVES": 5,
            "EXPLORATION_LOOKBACK_DAYS": 7,
            "DELIVERY_LOOKBACK_DAYS": 7,
            "DELIVERY_MIN_REQUESTS": 10,
            "DELIVERY_LOW_CLICK_RATE": 0.01,
            "DELIVERY_MIN_BUDGET_REMAINING_RATIO": 0.0,
            "DELIVERY_BOOST_VALUE": 0.0,
            "MARKET_HEALTH_WINDOW_MINUTES": 60,
            "MARKET_HEALTH_STREAK_SAMPLE": 10,
            "MARKET_HEALTH_FILL_LOW": 1.0,
            "MARKET_HEALTH_FILL_HIGH": 0.95,
            "MARKET_HEALTH_ELIGIBLE_SUPPLY_LOW": 999,
            "MARKET_HEALTH_REJECT_VOLATILITY_THRESHOLD": 999,
            "MARKET_HEALTH_UNFILLED_STREAK_THRESHOLD": 999,
            "MARKET_HEALTH_REJECT_HEALTHY": 0.0,
            "ALPHA_PROFIT_BOOST_LOW_FILL": 0.5,
            "ALPHA_PROFIT_BOOST_LOW_SUPPLY": 0.0,
            "BETA_CTR_BOOST_HEALTHY": 0.0,
            "GAMMA_TARGETING_BOOST_LOW_FILL": 0.3,
            "GAMMA_TARGETING_BOOST_UNFILLED": 0.0,
            "DELTA_QUALITY_BOOST_LOW_FILL": 0.2,
            "DELTA_QUALITY_BOOST_VOLATILITY": 0.0,
            "PARTNER_QUALITY_NEW_CLICKS": 0,
            "PARTNER_QUALITY_RECENT_DAYS": 1,
            "PARTNER_QUALITY_LONG_DAYS": 7,
            "PARTNER_QUALITY_RISKY_REJECT_RATE": 1.0,
            "PARTNER_QUALITY_RECOVER_REJECT_RATE": 0.0,
            "PARTNER_QUALITY_DELTA_NEW": 1.0,
            "PARTNER_QUALITY_DELTA_STABLE": 1.0,
            "PARTNER_QUALITY_DELTA_RISKY": 1.0,
            "PARTNER_QUALITY_DELTA_RECOVERING": 1.0,
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def create_user(email, role):
    user = User(email=email, role=role)
    user.set_password("pass")
    db.session.add(user)
    db.session.commit()
    return user


def create_campaign(buyer_id, name, category=None):
    partner_payout = compute_partner_payout(Decimal("2.00"))
    campaign = Campaign(
        buyer_id=buyer_id,
        name=name,
        status="active",
        budget_total=Decimal("100.00"),
        budget_spent=Decimal("0.00"),
        buyer_cpc=Decimal("2.00"),
        partner_payout=partner_payout,
        targeting_category=category,
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


def test_adaptive_multipliers_apply_to_score(client, app):
    with app.app_context():
        buyer = create_user("buyer@adaptive.com", "buyer")
        partner = create_user("partner@adaptive.com", "partner")
        campaign = create_campaign(buyer.id, "Adaptive", category="Fitness")
        create_ad(campaign.id, "Ad A")

    token = login_partner(client, "partner@adaptive.com")

    response = client.get(
        "/api/partner/ad?category=Fitness",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    breakdown = payload["score_breakdown"]

    assert breakdown["alpha_profit"] == pytest.approx(1.5)
    assert breakdown["gamma_targeting"] == pytest.approx(1.3)
    assert breakdown["beta_ctr"] == pytest.approx(1.0)

    expected_profit = 0.6
    expected_ctr = 0.01
    expected_score = expected_profit * 1.5 + (expected_ctr * 1.0 * 1.0) + (1.0 * 1.3)
    assert breakdown["total"] == pytest.approx(round(expected_score, 4))


def test_partner_quality_state_transitions(client, app):
    with app.app_context():
        app.config["PARTNER_QUALITY_NEW_CLICKS"] = 1
        app.config["PARTNER_QUALITY_RISKY_REJECT_RATE"] = 0.5
        app.config["PARTNER_QUALITY_RECOVER_REJECT_RATE"] = 0.4
        app.config["PARTNER_QUALITY_DELTA_RISKY"] = 1.5
        app.config["PARTNER_QUALITY_DELTA_RECOVERING"] = 1.1
        buyer = create_user("buyer@quality.com", "buyer")
        partner = create_user("partner@quality.com", "partner")
        campaign = create_campaign(buyer.id, "Quality")
        ad = create_ad(campaign.id, "Ad Q")
        partner_id = partner.id
        campaign_id = campaign.id
        ad_id = ad.id

        recent_ts = datetime.utcnow() - timedelta(hours=1)
        old_ts = datetime.utcnow() - timedelta(days=3)
        for _ in range(6):
            db.session.add(
                ClickEvent(
                    assignment_code="old-reject",
                    partner_id=partner.id,
                    campaign_id=campaign.id,
                    ad_id=ad.id,
                    ip_hash="hash",
                    ua_hash="ua",
                    status="REJECTED",
                    reject_reason="DUPLICATE_CLICK",
                    ts=old_ts,
                    spend_delta=Decimal("0"),
                    earnings_delta=Decimal("0"),
                    profit_delta=Decimal("0"),
                )
            )
        for _ in range(2):
            db.session.add(
                ClickEvent(
                    assignment_code="recent-reject",
                    partner_id=partner.id,
                    campaign_id=campaign.id,
                    ad_id=ad.id,
                    ip_hash="hash",
                    ua_hash="ua",
                    status="REJECTED",
                    reject_reason="DUPLICATE_CLICK",
                    ts=recent_ts,
                    spend_delta=Decimal("0"),
                    earnings_delta=Decimal("0"),
                    profit_delta=Decimal("0"),
                )
            )
        db.session.commit()

    token = login_partner(client, "partner@quality.com")
    first = client.get(
        "/api/partner/ad",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 200
    assert first.get_json()["score_breakdown"]["partner_quality_state"] == "RISKY"

    with app.app_context():
        for _ in range(4):
            db.session.add(
                ClickEvent(
                    assignment_code="recent-accept",
                    partner_id=partner_id,
                    campaign_id=campaign_id,
                    ad_id=ad_id,
                    ip_hash="hash",
                    ua_hash="ua",
                    status="ACCEPTED",
                    ts=datetime.utcnow(),
                    spend_delta=Decimal("0"),
                    earnings_delta=Decimal("0"),
                    profit_delta=Decimal("0"),
                )
            )
        db.session.commit()

    second = client.get(
        "/api/partner/ad",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second.status_code == 200
    assert second.get_json()["score_breakdown"]["partner_quality_state"] == "RECOVERING"


def test_exploration_capped_and_labeled(client, app):
    with app.app_context():
        app.config["EXPLORATION_RATE"] = 1.0
        app.config["EXPLORATION_BONUS"] = 0.3
        app.config["EXPLORATION_NEW_PARTNER_REQUESTS"] = 10
        app.config["EXPLORATION_NEW_AD_SERVES"] = 1
        app.config["EXPLORATION_MAX_AD_SERVES"] = 1
        buyer = create_user("buyer@explore.com", "buyer")
        create_user("partner@explore.com", "partner")
        campaign = create_campaign(buyer.id, "Explore")
        create_ad(campaign.id, "Ad E")

    token = login_partner(client, "partner@explore.com")
    first = client.get(
        "/api/partner/ad",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 200
    first_breakdown = first.get_json()["score_breakdown"]
    assert first_breakdown["exploration_applied"] is True

    second = client.get(
        "/api/partner/ad",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second.status_code == 200
    second_breakdown = second.get_json()["score_breakdown"]
    assert second_breakdown["exploration_applied"] is False


def test_delivery_boost_applied(client, app):
    with app.app_context():
        app.config["DELIVERY_BOOST_VALUE"] = 0.4
        app.config["DELIVERY_MIN_REQUESTS"] = 2
        app.config["DELIVERY_LOW_CLICK_RATE"] = 0.5
        buyer = create_user("buyer@delivery.com", "buyer")
        partner = create_user("partner@delivery.com", "partner")
        campaign = create_campaign(buyer.id, "Delivery")
        ad = create_ad(campaign.id, "Ad D")
        for _ in range(2):
            db.session.add(
                PartnerAdRequestEvent(
                    partner_id=partner.id,
                    campaign_id=campaign.id,
                    ad_id=ad.id,
                    filled=True,
                )
            )
        db.session.commit()

    token = login_partner(client, "partner@delivery.com")
    response = client.get(
        "/api/partner/ad",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    breakdown = response.get_json()["score_breakdown"]
    assert breakdown["delivery_boost_applied"] is True
    assert breakdown["delivery_boost"] == pytest.approx(0.4)
