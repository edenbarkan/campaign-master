from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib

from sqlalchemy import func, or_

from app.extensions import db
from app.models.ad import Ad
from app.models.assignment import AdAssignment
from app.models.campaign import Campaign
from app.models.click_event import ClickEvent
from app.models.impression_event import ImpressionEvent
from app.models.partner_ad_request_event import PartnerAdRequestEvent
from app.models.partner_ad_exposure import PartnerAdExposure
from app.services.market_health import build_market_health_snapshot, derive_adaptive_multipliers
from app.services.partner_quality import partner_quality_state, partner_reject_rate

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


def _deterministic_fraction(seed):
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _partner_request_count(partner_id, days):
    cutoff = _lookback_cutoff(days)
    return (
        PartnerAdRequestEvent.query.filter_by(partner_id=partner_id)
        .filter(PartnerAdRequestEvent.created_at >= cutoff)
        .count()
    )


def _partner_ad_serves(partner_id, ad_id, days):
    cutoff = _lookback_cutoff(days)
    return (
        PartnerAdRequestEvent.query.filter_by(
            partner_id=partner_id, ad_id=ad_id, filled=True
        )
        .filter(PartnerAdRequestEvent.created_at >= cutoff)
        .count()
    )


def _exploration_decision(
    partner_id,
    ad_id,
    exploration_rate,
    exploration_bonus,
    is_new_partner,
    is_new_ad,
):
    if exploration_rate <= 0:
        return False, 0, None
    if not (is_new_partner or is_new_ad):
        return False, 0, None

    bucket = _deterministic_fraction(f"{partner_id}:{ad_id}")
    if bucket <= exploration_rate:
        reason = "NEW_PARTNER" if is_new_partner else "NEW_AD"
        return True, exploration_bonus, reason
    return False, 0, None


def _delivery_boost(
    campaign,
    lookback_days,
    min_requests,
    low_click_rate,
    min_budget_remaining_ratio,
    boost_value,
):
    if boost_value <= 0:
        return 0

    budget_total = float(campaign.budget_total or 0)
    if budget_total:
        budget_remaining_ratio = float(campaign.budget_remaining) / budget_total
        if budget_remaining_ratio < min_budget_remaining_ratio:
            return 0

    cutoff = _lookback_cutoff(lookback_days)
    request_count = (
        PartnerAdRequestEvent.query.filter_by(campaign_id=campaign.id, filled=True)
        .filter(PartnerAdRequestEvent.created_at >= cutoff)
        .count()
    )
    if request_count < min_requests:
        return 0

    accepted_clicks = (
        ClickEvent.query.filter_by(campaign_id=campaign.id, status="ACCEPTED")
        .filter(ClickEvent.ts >= cutoff)
        .count()
    )
    click_rate = accepted_clicks / request_count if request_count else 0
    if click_rate < low_click_rate:
        return boost_value
    return 0


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
    exploration_rate=0.05,
    exploration_bonus=0.2,
    exploration_new_partner_requests=5,
    exploration_new_ad_serves=1,
    exploration_max_ad_serves=5,
    exploration_lookback_days=7,
    quality_recent_days=1,
    quality_long_days=7,
    quality_new_clicks=10,
    quality_risky_reject_rate=0.2,
    quality_recover_reject_rate=0.1,
    quality_delta_new=0.8,
    quality_delta_stable=1.0,
    quality_delta_risky=1.5,
    quality_delta_recovering=1.1,
    delivery_lookback_days=7,
    delivery_min_requests=10,
    delivery_low_click_rate=0.01,
    delivery_min_budget_remaining_ratio=0.5,
    delivery_boost_value=0.2,
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

    snapshot = build_market_health_snapshot()
    multipliers = derive_adaptive_multipliers(snapshot)
    alpha_profit = multipliers["alpha_profit"]
    beta_ctr = multipliers["beta_ctr"]
    gamma_targeting = multipliers["gamma_targeting"]
    market_delta_quality = multipliers["delta_quality"]
    market_note = multipliers["market_note"]

    quality = partner_quality_state(
        partner_id=partner_id,
        recent_days=quality_recent_days,
        long_days=quality_long_days,
        new_clicks_threshold=quality_new_clicks,
        risky_reject_rate=quality_risky_reject_rate,
        recovering_reject_rate=quality_recover_reject_rate,
        delta_multipliers={
            "NEW": quality_delta_new,
            "STABLE": quality_delta_stable,
            "RISKY": quality_delta_risky,
            "RECOVERING": quality_delta_recovering,
        },
    )
    partner_quality_state_value = quality["state"]
    partner_quality_note = quality["note"]
    partner_quality_multiplier = quality["delta_multiplier"]
    delta_quality = market_delta_quality * partner_quality_multiplier

    # Partner-level quality signal based on recent click decision events (accepted/rejected).
    partner_reject_rate_value = partner_reject_rate(partner_id, reject_lookback_days)

    partner_request_count = _partner_request_count(partner_id, exploration_lookback_days)
    is_new_partner = partner_request_count < exploration_new_partner_requests

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
        reject_penalty = partner_reject_rate_value * reject_penalty_weight
        quality_penalty = reject_penalty * delta_quality

        ad_serves = _partner_ad_serves(partner_id, ad.id, exploration_lookback_days)
        is_new_ad = ad_serves < exploration_new_ad_serves
        exploration_applied = False
        exploration_bonus_value = 0
        exploration_reason = None
        if ad_serves < exploration_max_ad_serves:
            exploration_applied, exploration_bonus_value, exploration_reason = (
                _exploration_decision(
                    partner_id,
                    ad.id,
                    exploration_rate,
                    exploration_bonus,
                    is_new_partner,
                    is_new_ad,
                )
            )

        delivery_boost = _delivery_boost(
            campaign,
            delivery_lookback_days,
            delivery_min_requests,
            delivery_low_click_rate,
            delivery_min_budget_remaining_ratio,
            delivery_boost_value,
        )

        score = (
            expected_profit * alpha_profit
            + (ctr * ctr_weight * beta_ctr)
            + (targeting_bonus * gamma_targeting)
            - quality_penalty
            + exploration_bonus_value
            + delivery_boost
        )

        assignment_count = (
            AdAssignment.query.filter_by(partner_id=partner_id, campaign_id=campaign.id)
            .count()
        )

        score_breakdown = {
            "profit": round(expected_profit, 4),
            "alpha_profit": round(alpha_profit, 4),
            "ctr": round(ctr, 4),
            "ctr_weight": round(ctr_weight, 4),
            "beta_ctr": round(beta_ctr, 4),
            "targeting_bonus": round(targeting_bonus, 4),
            "gamma_targeting": round(gamma_targeting, 4),
            "partner_reject_rate": round(partner_reject_rate_value, 4),
            "partner_reject_penalty": round(reject_penalty, 4),
            "partner_reject_lookback_days": reject_lookback_days,
            "partner_reject_penalty_weight": round(reject_penalty_weight, 4),
            "partner_quality_state": partner_quality_state_value,
            "partner_quality_note": partner_quality_note,
            "delta_quality": round(delta_quality, 4),
            "partner_quality_penalty": round(quality_penalty, 4),
            "exploration_applied": exploration_applied,
            "exploration_bonus": round(exploration_bonus_value, 4),
            "exploration_reason": exploration_reason,
            "delivery_boost": round(delivery_boost, 4),
            "delivery_boost_applied": delivery_boost > 0,
            "market_note": market_note,
            "total": round(score, 4),
        }

        explanation_parts = [
            f"Score balances profit ${expected_profit:.2f}, CTR {ctr:.2%}, "
            f"targeting bonus {targeting_bonus:.2f}."
        ]
        if market_note:
            explanation_parts.append(market_note)
        if partner_quality_note:
            explanation_parts.append(
                f"Partner quality state: {partner_quality_state_value}. {partner_quality_note}"
            )
        if exploration_applied and exploration_reason:
            explanation_parts.append(
                f"Exploration applied for {exploration_reason.replace('_', ' ').lower()}."
            )
        if delivery_boost > 0:
            explanation_parts.append("Delivery balancing boost applied for pacing.")

        explanation = " ".join(explanation_parts)

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
