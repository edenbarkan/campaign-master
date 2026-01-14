import os
import secrets
import time
from datetime import datetime, timedelta
from decimal import Decimal

import psycopg2

from app import create_app
from app.extensions import db
from app.models.ad import Ad
from app.models.assignment import AdAssignment
from app.models.campaign import Campaign
from app.models.click_event import ClickEvent
from app.models.impression_event import ImpressionEvent
from app.models.user import User
from app.services.pricing import compute_partner_payout
from app.services.validation import hash_value


def get_or_create_user(email, role, password):
    user = User.query.filter_by(email=email).first()
    if user:
        return user
    user = User(email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def get_or_create_campaign(buyer_id, name, max_cpc, budget_total, category, geo):
    campaign = Campaign.query.filter_by(buyer_id=buyer_id, name=name).first()
    if campaign:
        return campaign
    partner_payout = compute_partner_payout(Decimal(max_cpc))
    campaign = Campaign(
        buyer_id=buyer_id,
        name=name,
        status="active",
        budget_total=Decimal(budget_total),
        budget_spent=Decimal("0.00"),
        buyer_cpc=Decimal(max_cpc),
        partner_payout=partner_payout,
        targeting_category=category,
        targeting_geo=geo,
    )
    db.session.add(campaign)
    db.session.commit()
    return campaign


def get_or_create_ad(campaign_id, title, body, image_url, destination_url):
    ad = Ad.query.filter_by(campaign_id=campaign_id, title=title).first()
    if ad:
        return ad
    ad = Ad(
        campaign_id=campaign_id,
        title=title,
        body=body,
        image_url=image_url,
        destination_url=destination_url,
        active=True,
    )
    db.session.add(ad)
    db.session.commit()
    return ad


def seed_events(campaign, ad, partner):
    existing = (
        ClickEvent.query.filter_by(campaign_id=campaign.id, partner_id=partner.id).count()
    )
    if existing > 0:
        return

    assignment = AdAssignment(
        code=secrets.token_urlsafe(8).rstrip("="),
        partner_id=partner.id,
        campaign_id=campaign.id,
        ad_id=ad.id,
        category=campaign.targeting_category,
        geo=campaign.targeting_geo,
        placement="sidebar",
        device="desktop",
    )
    db.session.add(assignment)
    db.session.commit()

    spend = Decimal("0.00")
    ip_hash = hash_value("127.0.0.1")
    ua_hash = hash_value("seed-agent")

    for offset in range(7):
        day = datetime.utcnow() - timedelta(days=offset)
        for _ in range(30 - offset * 2):
            db.session.add(
                ImpressionEvent(
                    assignment_code=assignment.code,
                    campaign_id=campaign.id,
                    ad_id=ad.id,
                    partner_id=partner.id,
                    ip_hash=ip_hash,
                    status="ACCEPTED",
                    ts=day,
                )
            )
        for _ in range(6 - offset // 2):
            db.session.add(
                ClickEvent(
                    assignment_code=assignment.code,
                    campaign_id=campaign.id,
                    ad_id=ad.id,
                    partner_id=partner.id,
                    ip_hash=ip_hash,
                    ua_hash=ua_hash,
                    status="ACCEPTED",
                    spend_delta=campaign.buyer_cpc,
                    earnings_delta=campaign.partner_payout,
                    profit_delta=campaign.buyer_cpc - campaign.partner_payout,
                    ts=day,
                )
            )
            spend += campaign.buyer_cpc

    db.session.add(
        ClickEvent(
            assignment_code=assignment.code,
            campaign_id=campaign.id,
            ad_id=ad.id,
            partner_id=partner.id,
            ip_hash=ip_hash,
            ua_hash=ua_hash,
            status="REJECTED",
            reject_reason="DUPLICATE_CLICK",
            ts=datetime.utcnow(),
        )
    )

    campaign.budget_spent = spend
    db.session.commit()


def seed_demo_data():
    buyer = get_or_create_user("buyer@demo.com", "buyer", "buyerpass")
    partner = get_or_create_user("partner@demo.com", "partner", "partnerpass")
    get_or_create_user("admin@demo.com", "admin", "adminpass")

    campaign = get_or_create_campaign(
        buyer.id,
        "Pulse Launch",
        "2.50",
        "1500.00",
        "Fitness",
        "US",
    )
    ad = get_or_create_ad(
        campaign.id,
        "Sprint in Sync",
        "Performance sneakers for daily training.",
        "https://images.unsplash.com/flagged/photo-1556745757-8d76bdb6984b",
        "https://example.com/sprint",
    )

    seed_events(campaign, ad, partner)


def wait_for_db(max_seconds=30):
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return

    deadline = time.time() + max_seconds
    while time.time() < deadline:
        try:
            conn = psycopg2.connect(database_url)
            conn.close()
            return
        except Exception:
            time.sleep(1)

    raise RuntimeError("Database connection failed after retries")


def main():
    wait_for_db()
    app = create_app()
    with app.app_context():
        seed_demo_data()
    print("Seeded demo data.")


if __name__ == "__main__":
    main()
