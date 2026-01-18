from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, or_

from app.extensions import db
from app.models.ad import Ad
from app.models.assignment import AdAssignment
from app.models.campaign import Campaign
from app.models.click_event import ClickEvent
from app.models.impression_event import ImpressionEvent
from app.models.partner_ad_exposure import PartnerAdExposure

DEFAULT_CTR = 0.01


@dataclass
class MatchResult:
    ad: Ad | None
    campaign: Campaign | None
    explanation: str | None
    score_breakdown: dict
    unfilled_reason: str | None
    debug_candidates: list | None = None


def _ctr(clicks, impressions):
    if impressions and impressions > 0:
        return clicks / impressions
    return None


def _smoothed_ctr(clicks, impressions):
    return (clicks + 1) / (impressions + 10)


def _ctr_counts(query_clicks, query_impressions):
    clicks = query_clicks.scalar() or 0
    impressions = query_impressions.scalar() or 0
    return clicks, impressions


def _lookback_cutoff(days):
    return datetime.utcnow() - timedelta(days=days)


def _ad_ctr(partner_id, ad_id, days):
    cutoff = _lookback_cutoff(days)
    clicks, impressions = _ctr_counts(
        db.session.query(func.count(ClickEvent.id))
        .filter(ClickEvent.partner_id == partner_id)
        .filter(ClickEvent.ad_id == ad_id)
        .filter(ClickEvent.status == "ACCEPTED")
        .filter(ClickEvent.ts >= cutoff),
        db.session.query(func.count(ImpressionEvent.id))
        .filter(ImpressionEvent.partner_id == partner_id)
        .filter(ImpressionEvent.ad_id == ad_id)
        .filter(ImpressionEvent.status == "ACCEPTED")
        .filter(ImpressionEvent.ts >= cutoff),
    )
    return clicks, impressions


def _campaign_ctr(partner_id, campaign_id, days):
    cutoff = _lookback_cutoff(days)
    clicks, impressions = _ctr_counts(
        db.session.query(func.count(ClickEvent.id))
        .filter(ClickEvent.partner_id == partner_id)
        .filter(ClickEvent.campaign_id == campaign_id)
        .filter(ClickEvent.status == "ACCEPTED")
        .filter(ClickEvent.ts >= cutoff),
        db.session.query(func.count(ImpressionEvent.id))
        .filter(ImpressionEvent.partner_id == partner_id)
        .filter(ImpressionEvent.campaign_id == campaign_id)
        .filter(ImpressionEvent.status == "ACCEPTED")
        .filter(ImpressionEvent.ts >= cutoff),
    )
    return clicks, impressions


def _global_campaign_ctr(campaign_id, days):
    cutoff = _lookback_cutoff(days)
    clicks, impressions = _ctr_counts(
        db.session.query(func.count(ClickEvent.id))
        .filter(ClickEvent.campaign_id == campaign_id)
        .filter(ClickEvent.status == "ACCEPTED")
        .filter(ClickEvent.ts >= cutoff),
        db.session.query(func.count(ImpressionEvent.id))
        .filter(ImpressionEvent.campaign_id == campaign_id)
        .filter(ImpressionEvent.status == "ACCEPTED")
        .filter(ImpressionEvent.ts >= cutoff),
    )
    return clicks, impressions


def _partner_reject_rate(partner_id, days):
    cutoff = _lookback_cutoff(days)
    accepted = (
        db.session.query(func.count(ClickEvent.id))
        .filter(ClickEvent.partner_id == partner_id)
        .filter(ClickEvent.status == "ACCEPTED")
        .filter(ClickEvent.ts >= cutoff)
        .scalar()
        or 0
    )
    rejected = (
        db.session.query(func.count(ClickEvent.id))
        .filter(ClickEvent.partner_id == partner_id)
        .filter(ClickEvent.status == "REJECTED")
        .filter(ClickEvent.ts >= cutoff)
        .scalar()
        or 0
    )
    total = accepted + rejected
    return rejected / total if total else 0


def _targeting_bonus(campaign, category, geo, device, placement, bonus_value):
    bonus = 0
    if category and campaign.targeting_category and campaign.targeting_category == category:
        bonus += bonus_value
    if geo and campaign.targeting_geo and campaign.targeting_geo == geo:
        bonus += bonus_value
    if device and campaign.targeting_device and campaign.targeting_device == device:
        bonus += bonus_value
    if placement and campaign.targeting_placement and campaign.targeting_placement == placement:
        bonus += bonus_value
    return bonus


def _exposure_blocked(partner_id, ad_id, freq_cap_seconds):
    cutoff = datetime.utcnow() - timedelta(seconds=freq_cap_seconds)
    exposure = (
        PartnerAdExposure.query.filter_by(partner_id=partner_id, ad_id=ad_id)
        .filter(PartnerAdExposure.last_served_at >= cutoff)
        .first()
    )
    return exposure is not None


def select_ad_for_partner(
    partner_id,
    category=None,
    geo=None,
    device=None,
    placement=None,
    freq_cap_seconds=60,
    ctr_lookback_days=14,
    reject_lookback_days=7,
    ctr_weight=1.0,
    targeting_bonus_value=0.5,
    reject_penalty_weight=1.0,
    debug=False,
    debug_limit=3,
):
    today = datetime.utcnow().date()

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
    blocked_by_cap = 0

    # Partner-level quality signal based on recent click decisions (accepted/rejected).
    partner_reject_rate = _partner_reject_rate(partner_id, reject_lookback_days)

    for campaign in campaigns.order_by(Campaign.id.asc()).all():
        ad = (
            Ad.query.filter_by(campaign_id=campaign.id, active=True)
            .order_by(Ad.id.asc())
            .first()
        )
        if not ad:
            continue

        if freq_cap_seconds and _exposure_blocked(partner_id, ad.id, freq_cap_seconds):
            blocked_by_cap += 1
            continue

        ad_clicks, ad_impressions = _ad_ctr(partner_id, ad.id, ctr_lookback_days)
        if ad_impressions == 0:
            ad_clicks, ad_impressions = _campaign_ctr(
                partner_id, campaign.id, ctr_lookback_days
            )
        if ad_impressions == 0:
            ad_clicks, ad_impressions = _global_campaign_ctr(
                campaign.id, ctr_lookback_days
            )

        if ad_impressions == 0:
            ctr = DEFAULT_CTR
        else:
            ctr = _smoothed_ctr(ad_clicks, ad_impressions)

        expected_profit = float(campaign.buyer_cpc - campaign.partner_payout)
        targeting_bonus = _targeting_bonus(
            campaign, category, geo, device, placement, targeting_bonus_value
        )
        # Apply partner-quality penalty uniformly across all candidate ads.
        reject_penalty = partner_reject_rate * reject_penalty_weight

        score = expected_profit + (ctr * ctr_weight) + targeting_bonus - reject_penalty

        assignment_count = (
            AdAssignment.query.filter_by(partner_id=partner_id, campaign_id=campaign.id)
            .count()
        )

        score_breakdown = {
            "profit": round(expected_profit, 4),
            "ctr": round(ctr, 4),
            "ctr_weight": round(ctr_weight, 4),
            "targeting_bonus": round(targeting_bonus, 4),
            "partner_reject_rate": round(partner_reject_rate, 4),
            "partner_reject_penalty": round(reject_penalty, 4),
            "partner_reject_lookback_days": reject_lookback_days,
            "partner_reject_penalty_weight": round(reject_penalty_weight, 4),
            "total": round(score, 4),
        }

        explanation = (
            f"Score balances profit ${expected_profit:.2f}, CTR {ctr:.2%}, "
            f"targeting bonus {targeting_bonus:.2f}, and partner reject rate "
            f"{partner_reject_rate:.2%}."
        )

        candidates.append(
            (
                score,
                assignment_count,
                campaign.id,
                ad.id,
                campaign,
                ad,
                explanation,
                score_breakdown,
            )
        )

    if not candidates:
        reason = "FREQ_CAP" if blocked_by_cap else "NO_ELIGIBLE_ADS"
        return MatchResult(None, None, None, {}, reason, [])

    candidates.sort(key=lambda item: (-item[0], item[1], item[2], item[3]))
    _, _, _, _, campaign, ad, explanation, score_breakdown = candidates[0]
    debug_candidates = None
    if debug:
        debug_candidates = [
            {
                "campaign_id": entry[4].id,
                "ad_id": entry[5].id,
                "score": round(entry[0], 4),
                "score_breakdown": entry[7],
            }
            for entry in candidates[:debug_limit]
        ]
    return MatchResult(ad, campaign, explanation, score_breakdown, None, debug_candidates)
