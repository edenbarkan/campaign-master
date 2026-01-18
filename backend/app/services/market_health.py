from datetime import datetime, timedelta

from flask import current_app, has_app_context
from sqlalchemy import func

from app.extensions import db
from app.models.ad import Ad
from app.models.campaign import Campaign
from app.models.click_event import ClickEvent
from app.models.partner_ad_request_event import PartnerAdRequestEvent


def _get_config(key, default):
    if has_app_context():
        return current_app.config.get(key, default)
    return default


def build_market_health_snapshot():
    window_minutes = int(_get_config("MARKET_HEALTH_WINDOW_MINUTES", 60))
    window_delta = timedelta(minutes=window_minutes)
    now = datetime.utcnow()
    cutoff = now - window_delta
    previous_cutoff = cutoff - window_delta

    total_requests = (
        PartnerAdRequestEvent.query.filter(PartnerAdRequestEvent.created_at >= cutoff).count()
    )
    filled_requests = (
        PartnerAdRequestEvent.query.filter(PartnerAdRequestEvent.created_at >= cutoff)
        .filter(PartnerAdRequestEvent.filled.is_(True))
        .count()
    )
    fill_rate = filled_requests / total_requests if total_requests else 0

    rejected = (
        ClickEvent.query.filter(ClickEvent.ts >= cutoff)
        .filter(ClickEvent.status == "REJECTED")
        .count()
    )
    accepted = (
        ClickEvent.query.filter(ClickEvent.ts >= cutoff)
        .filter(ClickEvent.status == "ACCEPTED")
        .count()
    )
    total_clicks = accepted + rejected
    reject_rate = rejected / total_clicks if total_clicks else 0

    prev_rejected = (
        ClickEvent.query.filter(ClickEvent.ts < cutoff)
        .filter(ClickEvent.ts >= previous_cutoff)
        .filter(ClickEvent.status == "REJECTED")
        .count()
    )
    prev_accepted = (
        ClickEvent.query.filter(ClickEvent.ts < cutoff)
        .filter(ClickEvent.ts >= previous_cutoff)
        .filter(ClickEvent.status == "ACCEPTED")
        .count()
    )
    prev_total = prev_accepted + prev_rejected
    prev_reject_rate = prev_rejected / prev_total if prev_total else 0
    reject_volatility = abs(reject_rate - prev_reject_rate)

    eligible_ads = (
        db.session.query(func.count(Ad.id))
        .join(Campaign, Ad.campaign_id == Campaign.id)
        .filter(Ad.active.is_(True))
        .filter(Campaign.status == "active")
        .filter(Campaign.budget_spent + Campaign.buyer_cpc <= Campaign.budget_total)
        .scalar()
        or 0
    )
    eligible_ads_per_request = (
        eligible_ads / total_requests if total_requests else float(eligible_ads)
    )

    recent_requests = (
        PartnerAdRequestEvent.query.order_by(PartnerAdRequestEvent.created_at.desc())
        .limit(int(_get_config("MARKET_HEALTH_STREAK_SAMPLE", 10)))
        .all()
    )
    unfilled_streak = 0
    for event in recent_requests:
        if event.filled:
            break
        unfilled_streak += 1

    return {
        "fill_rate": fill_rate,
        "reject_rate": reject_rate,
        "reject_volatility": reject_volatility,
        "eligible_ads_per_request": eligible_ads_per_request,
        "unfilled_streak": unfilled_streak,
    }


def derive_adaptive_multipliers(snapshot):
    alpha_profit = 1.0
    beta_ctr = 1.0
    gamma_targeting = 1.0
    delta_quality = 1.0
    notes = []

    fill_low = float(_get_config("MARKET_HEALTH_FILL_LOW", 0.5))
    fill_high = float(_get_config("MARKET_HEALTH_FILL_HIGH", 0.8))
    eligible_low = float(_get_config("MARKET_HEALTH_ELIGIBLE_SUPPLY_LOW", 0.5))
    volatility_threshold = float(
        _get_config("MARKET_HEALTH_REJECT_VOLATILITY_THRESHOLD", 0.1)
    )
    unfilled_threshold = int(_get_config("MARKET_HEALTH_UNFILLED_STREAK_THRESHOLD", 3))
    reject_rate_healthy = float(_get_config("MARKET_HEALTH_REJECT_HEALTHY", 0.05))

    profit_boost_low_fill = float(_get_config("ALPHA_PROFIT_BOOST_LOW_FILL", 0.2))
    ctr_boost_healthy = float(_get_config("BETA_CTR_BOOST_HEALTHY", 0.1))
    targeting_boost_low_fill = float(
        _get_config("GAMMA_TARGETING_BOOST_LOW_FILL", 0.1)
    )
    targeting_boost_unfilled = float(
        _get_config("GAMMA_TARGETING_BOOST_UNFILLED", 0.1)
    )
    quality_boost_low_fill = float(
        _get_config("DELTA_QUALITY_BOOST_LOW_FILL", 0.2)
    )
    quality_boost_volatility = float(
        _get_config("DELTA_QUALITY_BOOST_VOLATILITY", 0.1)
    )
    profit_boost_low_supply = float(
        _get_config("ALPHA_PROFIT_BOOST_LOW_SUPPLY", 0.1)
    )

    if snapshot["fill_rate"] < fill_low:
        alpha_profit += profit_boost_low_fill
        gamma_targeting += targeting_boost_low_fill
        delta_quality += quality_boost_low_fill
        notes.append("Tight supply: emphasizing profit, targeting, and quality.")

    if snapshot["fill_rate"] > fill_high and snapshot["reject_rate"] < reject_rate_healthy:
        beta_ctr += ctr_boost_healthy
        notes.append("Healthy demand: modestly emphasizing CTR.")

    if snapshot["eligible_ads_per_request"] < eligible_low:
        alpha_profit += profit_boost_low_supply
        notes.append("Low eligible supply: prioritizing profit.")

    if snapshot["unfilled_streak"] >= unfilled_threshold:
        gamma_targeting += targeting_boost_unfilled
        notes.append("Recent unfilled streak: boosting targeting match.")

    if snapshot["reject_volatility"] > volatility_threshold:
        delta_quality += quality_boost_volatility
        notes.append("Reject volatility: tightening quality penalty.")

    market_note = "Market stable." if not notes else " ".join(notes)

    return {
        "alpha_profit": round(alpha_profit, 4),
        "beta_ctr": round(beta_ctr, 4),
        "gamma_targeting": round(gamma_targeting, 4),
        "delta_quality": round(delta_quality, 4),
        "market_note": market_note,
    }
