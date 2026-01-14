from datetime import date

from sqlalchemy import func, or_

from app.extensions import db
from app.models.ad import Ad
from app.models.assignment import AdAssignment
from app.models.campaign import Campaign
from app.models.click_event import ClickEvent
from app.models.impression_event import ImpressionEvent

DEFAULT_CTR = 0.01


def _ctr(clicks, impressions):
    if impressions and impressions > 0:
        return clicks / impressions
    return None


def _campaign_ctr(campaign_id):
    clicks = (
        db.session.query(func.count(ClickEvent.id))
        .filter(ClickEvent.campaign_id == campaign_id)
        .filter(ClickEvent.status == "ACCEPTED")
        .scalar()
        or 0
    )
    impressions = (
        db.session.query(func.count(ImpressionEvent.id))
        .filter(ImpressionEvent.campaign_id == campaign_id)
        .filter(ImpressionEvent.status == "ACCEPTED")
        .scalar()
        or 0
    )
    return _ctr(clicks, impressions)


def _partner_ctr(campaign_id, partner_id):
    clicks = (
        db.session.query(func.count(ClickEvent.id))
        .filter(ClickEvent.campaign_id == campaign_id)
        .filter(ClickEvent.partner_id == partner_id)
        .filter(ClickEvent.status == "ACCEPTED")
        .scalar()
        or 0
    )
    impressions = (
        db.session.query(func.count(ImpressionEvent.id))
        .filter(ImpressionEvent.campaign_id == campaign_id)
        .filter(ImpressionEvent.partner_id == partner_id)
        .filter(ImpressionEvent.status == "ACCEPTED")
        .scalar()
        or 0
    )
    return _ctr(clicks, impressions)


def select_ad_for_partner(partner_id, category=None, geo=None, device=None, placement=None):
    today = date.today()

    campaigns = (
        Campaign.query.filter(Campaign.status == "active")
        .filter(Campaign.budget_spent + Campaign.buyer_cpc <= Campaign.budget_total)
        .filter(or_(Campaign.start_date.is_(None), Campaign.start_date <= today))
        .filter(or_(Campaign.end_date.is_(None), Campaign.end_date >= today))
    )

    if category:
        campaigns = campaigns.filter(
            or_(Campaign.targeting_category.is_(None), Campaign.targeting_category == category)
        )

    if geo:
        campaigns = campaigns.filter(
            or_(Campaign.targeting_geo.is_(None), Campaign.targeting_geo == geo)
        )

    if device:
        campaigns = campaigns.filter(
            or_(Campaign.targeting_device.is_(None), Campaign.targeting_device == device)
        )

    if placement:
        campaigns = campaigns.filter(
            or_(Campaign.targeting_placement.is_(None), Campaign.targeting_placement == placement)
        )

    candidates = []

    for campaign in campaigns.order_by(Campaign.id.asc()).all():
        ad = (
            Ad.query.filter_by(campaign_id=campaign.id, active=True)
            .order_by(Ad.id.asc())
            .first()
        )
        if not ad:
            continue

        expected_ctr = _partner_ctr(campaign.id, partner_id)
        if expected_ctr is None:
            expected_ctr = _campaign_ctr(campaign.id)
        if expected_ctr is None:
            expected_ctr = DEFAULT_CTR

        expected_profit = float(expected_ctr) * float(campaign.buyer_cpc) - float(
            campaign.partner_payout
        )

        assignment_count = (
            AdAssignment.query.filter_by(partner_id=partner_id, campaign_id=campaign.id)
            .count()
        )

        candidates.append((expected_profit, assignment_count, campaign, ad))

    if not candidates:
        return None, None

    candidates.sort(key=lambda item: (-item[0], item[1], item[2].id))
    _, _, campaign, ad = candidates[0]
    return ad, campaign
