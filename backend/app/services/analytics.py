import json
from datetime import date, timedelta

from sqlalchemy import case, func
from flask import current_app

from app.extensions import db
from app.models.ad import Ad
from app.models.campaign import Campaign
from app.models.click_event import ClickEvent
from app.models.impression_event import ImpressionEvent
from app.models.partner_ad_request_event import PartnerAdRequestEvent
from app.models.user import User
from app.services.market_health import build_market_health_snapshot, derive_adaptive_multipliers
from app.services.partner_quality import partner_quality_state, partner_reject_rate


def _normalize_day(value):
    if isinstance(value, str):
        return date.fromisoformat(value)
    return value


def build_daily_series(click_rows, impression_rows, days):
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)
    row_map = {}

    for row in click_rows:
        row_map[_normalize_day(row.day)] = {
            "spend": float(row.spend or 0),
            "earnings": float(row.earnings or 0),
            "profit": float(row.profit or 0),
            "clicks": int(row.clicks or 0),
            "impressions": 0,
        }

    for row in impression_rows:
        day_value = _normalize_day(row.day)
        payload = row_map.setdefault(
            day_value,
            {
                "spend": 0,
                "earnings": 0,
                "profit": 0,
                "clicks": 0,
                "impressions": 0,
            },
        )
        payload["impressions"] = int(row.impressions or 0)

    series = []
    for offset in range(days):
        current_day = start_date + timedelta(days=offset)
        payload = row_map.get(
            current_day,
            {
                "spend": 0,
                "earnings": 0,
                "profit": 0,
                "clicks": 0,
                "impressions": 0,
            },
        )
        series.append(
            {
                "date": current_day.isoformat(),
                "spend": payload["spend"],
                "earnings": payload["earnings"],
                "profit": payload["profit"],
                "clicks": payload["clicks"],
                "impressions": payload["impressions"],
            }
        )

    return series


def build_risk_series(rows, start_date, end_date):
    row_map = {}
    for row in rows:
        row_map[_normalize_day(row.day)] = {
            "accepted": int(row.accepted or 0),
            "rejected": int(row.rejected or 0),
        }

    series = []
    total_days = (end_date - start_date).days + 1
    for offset in range(total_days):
        current_day = start_date + timedelta(days=offset)
        payload = row_map.get(current_day, {"accepted": 0, "rejected": 0})
        series.append(
            {
                "date": current_day.isoformat(),
                "accepted": payload["accepted"],
                "rejected": payload["rejected"],
            }
        )
    return series


def _click_rows_for_campaign_filter(campaign_filter, start_date):
    return (
        db.session.query(
            func.date(ClickEvent.ts).label("day"),
            func.count(ClickEvent.id).label("clicks"),
            func.sum(ClickEvent.spend_delta).label("spend"),
            func.sum(ClickEvent.earnings_delta).label("earnings"),
            func.sum(ClickEvent.profit_delta).label("profit"),
        )
        .join(Campaign, ClickEvent.campaign_id == Campaign.id)
        .filter(campaign_filter)
        .filter(ClickEvent.status == "ACCEPTED")
        .filter(ClickEvent.ts >= start_date)
        .group_by("day")
        .all()
    )


def _impression_rows_for_campaign_filter(campaign_filter, start_date):
    return (
        db.session.query(
            func.date(ImpressionEvent.ts).label("day"),
            func.count(ImpressionEvent.id).label("impressions"),
        )
        .join(Campaign, ImpressionEvent.campaign_id == Campaign.id)
        .filter(campaign_filter)
        .filter(ImpressionEvent.status == "ACCEPTED")
        .filter(ImpressionEvent.ts >= start_date)
        .group_by("day")
        .all()
    )


def buyer_daily_metrics(buyer_id, days=14):
    start_date = date.today() - timedelta(days=days - 1)

    click_rows = _click_rows_for_campaign_filter(Campaign.buyer_id == buyer_id, start_date)
    impression_rows = _impression_rows_for_campaign_filter(
        Campaign.buyer_id == buyer_id, start_date
    )
    return build_daily_series(click_rows, impression_rows, days)


def partner_daily_metrics(partner_id, days=14):
    start_date = date.today() - timedelta(days=days - 1)

    click_rows = (
        db.session.query(
            func.date(ClickEvent.ts).label("day"),
            func.count(ClickEvent.id).label("clicks"),
            func.sum(ClickEvent.spend_delta).label("spend"),
            func.sum(ClickEvent.earnings_delta).label("earnings"),
            func.sum(ClickEvent.profit_delta).label("profit"),
        )
        .filter(ClickEvent.partner_id == partner_id)
        .filter(ClickEvent.status == "ACCEPTED")
        .filter(ClickEvent.ts >= start_date)
        .group_by("day")
        .all()
    )

    impression_rows = (
        db.session.query(
            func.date(ImpressionEvent.ts).label("day"),
            func.count(ImpressionEvent.id).label("impressions"),
        )
        .filter(ImpressionEvent.partner_id == partner_id)
        .filter(ImpressionEvent.status == "ACCEPTED")
        .filter(ImpressionEvent.ts >= start_date)
        .group_by("day")
        .all()
    )

    return build_daily_series(click_rows, impression_rows, days)


def buyer_campaign_table(buyer_id):
    campaigns = Campaign.query.filter_by(buyer_id=buyer_id).order_by(Campaign.id.desc()).all()
    results = []

    for campaign in campaigns:
        click_stats = (
            db.session.query(
                func.count(ClickEvent.id).label("clicks"),
                func.sum(ClickEvent.spend_delta).label("spend"),
            )
            .filter(ClickEvent.campaign_id == campaign.id)
            .filter(ClickEvent.status == "ACCEPTED")
            .first()
        )
        click_count = int(click_stats.clicks or 0)
        spend = float(click_stats.spend or 0)

        impressions = (
            db.session.query(func.count(ImpressionEvent.id))
            .filter(ImpressionEvent.campaign_id == campaign.id)
            .filter(ImpressionEvent.status == "ACCEPTED")
            .scalar()
            or 0
        )
        ctr = click_count / impressions if impressions else 0

        partner_rows = (
            db.session.query(
                User.id,
                User.email,
                func.count(ClickEvent.id).label("clicks"),
            )
            .join(ClickEvent, ClickEvent.partner_id == User.id)
            .filter(
                ClickEvent.campaign_id == campaign.id,
                ClickEvent.status == "ACCEPTED",
            )
            .group_by(User.id, User.email)
            .order_by(func.count(ClickEvent.id).desc())
            .limit(3)
            .all()
        )

        results.append(
            {
                "id": campaign.id,
                "name": campaign.name,
                "status": campaign.status,
                "spend": spend,
                "clicks": click_count,
                "impressions": int(impressions),
                "ctr": ctr,
                "budget_remaining": float(campaign.budget_remaining),
                "top_partners": [
                    {
                        "id": row.id,
                        "email": row.email,
                        "clicks": int(row.clicks),
                    }
                    for row in partner_rows
                ],
            }
        )

    return results


def partner_campaign_table(partner_id):
    rows = (
        db.session.query(
            Campaign.id,
            Campaign.name,
            func.count(ClickEvent.id).label("clicks"),
            func.sum(ClickEvent.earnings_delta).label("earnings"),
        )
        .join(Campaign, ClickEvent.campaign_id == Campaign.id)
        .filter(ClickEvent.partner_id == partner_id)
        .filter(ClickEvent.status == "ACCEPTED")
        .group_by(Campaign.id, Campaign.name)
        .order_by(func.sum(ClickEvent.earnings_delta).desc())
        .all()
    )

    return [
        {
            "id": row.id,
            "name": row.name,
            "clicks": int(row.clicks or 0),
            "earnings": float(row.earnings or 0),
        }
        for row in rows
    ]


def partner_top_ads(partner_id, limit=5):
    rows = (
        db.session.query(
            Ad.id,
            Ad.title,
            func.count(ClickEvent.id).label("clicks"),
            func.sum(ClickEvent.earnings_delta).label("earnings"),
        )
        .join(ClickEvent, ClickEvent.ad_id == Ad.id)
        .filter(ClickEvent.partner_id == partner_id)
        .filter(ClickEvent.status == "ACCEPTED")
        .group_by(Ad.id, Ad.title)
        .order_by(func.sum(ClickEvent.earnings_delta).desc())
        .limit(limit)
        .all()
    )

    results = []
    for row in rows:
        impressions = (
            db.session.query(func.count(ImpressionEvent.id))
            .filter(ImpressionEvent.partner_id == partner_id)
            .filter(ImpressionEvent.ad_id == row.id)
            .filter(ImpressionEvent.status == "ACCEPTED")
            .scalar()
            or 0
        )
        ctr = int(row.clicks or 0) / impressions if impressions else 0
        results.append(
            {
                "id": row.id,
                "title": row.title,
                "clicks": int(row.clicks or 0),
                "earnings": float(row.earnings or 0),
                "ctr": ctr,
            }
        )

    return results


def partner_request_stats(partner_id):
    total_requests = (
        PartnerAdRequestEvent.query.filter_by(partner_id=partner_id).count()
    )
    filled_requests = (
        PartnerAdRequestEvent.query.filter_by(partner_id=partner_id, filled=True).count()
    )
    unfilled_requests = total_requests - filled_requests
    fill_rate = filled_requests / total_requests if total_requests else 0
    return {
        "total_requests": total_requests,
        "filled_requests": filled_requests,
        "unfilled_requests": unfilled_requests,
        "fill_rate": fill_rate,
    }


def partner_latest_request(partner_id):
    event = (
        PartnerAdRequestEvent.query.filter_by(partner_id=partner_id, filled=True)
        .order_by(PartnerAdRequestEvent.created_at.desc())
        .first()
    )
    if not event:
        return None

    breakdown = {}
    if event.score_breakdown:
        try:
            breakdown = json.loads(event.score_breakdown)
        except json.JSONDecodeError:
            breakdown = {}

    # Normalize partner-quality keys for legacy stored breakdowns.
    if "partner_reject_penalty" not in breakdown and "reject_penalty" in breakdown:
        breakdown["partner_reject_penalty"] = breakdown.get("reject_penalty", 0)
    if "partner_reject_rate" not in breakdown:
        breakdown["partner_reject_rate"] = 0
    if "partner_reject_penalty_weight" not in breakdown:
        breakdown["partner_reject_penalty_weight"] = 1
    if "alpha_profit" not in breakdown:
        breakdown["alpha_profit"] = 1
    if "beta_ctr" not in breakdown:
        breakdown["beta_ctr"] = 1
    if "gamma_targeting" not in breakdown:
        breakdown["gamma_targeting"] = 1
    if "delta_quality" not in breakdown:
        breakdown["delta_quality"] = 1
    if "partner_quality_state" not in breakdown:
        breakdown["partner_quality_state"] = "UNKNOWN"
    if "partner_quality_penalty" not in breakdown:
        base_penalty = breakdown.get("partner_reject_penalty", 0)
        breakdown["partner_quality_penalty"] = base_penalty * breakdown.get("delta_quality", 1)
    if "exploration_applied" not in breakdown:
        breakdown["exploration_applied"] = False
    if "exploration_bonus" not in breakdown:
        breakdown["exploration_bonus"] = 0
    if "delivery_boost" not in breakdown:
        breakdown["delivery_boost"] = 0
    if "delivery_boost_applied" not in breakdown:
        breakdown["delivery_boost_applied"] = False

    return {
        "ad": {
            "id": event.ad_id,
            "title": event.ad.title if event.ad else None,
        },
        "explanation": event.explanation,
        "score_breakdown": breakdown,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


def buyer_request_stats(buyer_id):
    campaigns = Campaign.query.filter_by(buyer_id=buyer_id, status="active").all()
    campaign_ids = [campaign.id for campaign in campaigns]
    if not campaign_ids:
        return {"fill_rate": 0, "total_requests": 0, "filled_requests": 0}

    filled_requests = (
        PartnerAdRequestEvent.query.filter(
            PartnerAdRequestEvent.filled.is_(True),
            PartnerAdRequestEvent.campaign_id.in_(campaign_ids),
        ).count()
    )

    unfilled_events = PartnerAdRequestEvent.query.filter_by(filled=False).all()
    unfilled_requests = 0
    for event in unfilled_events:
        for campaign in campaigns:
            if campaign.targeting_category and event.category:
                if campaign.targeting_category != event.category:
                    continue
            if campaign.targeting_geo and event.geo:
                if campaign.targeting_geo != event.geo:
                    continue
            if campaign.targeting_device and event.device:
                if campaign.targeting_device != event.device:
                    continue
            if campaign.targeting_placement and event.placement:
                if campaign.targeting_placement != event.placement:
                    continue
            unfilled_requests += 1
            break

    total_requests = filled_requests + unfilled_requests
    fill_rate = filled_requests / total_requests if total_requests else 0
    return {
        "fill_rate": fill_rate,
        "total_requests": total_requests,
        "filled_requests": filled_requests,
    }


def buyer_delivery_status(buyer_id):
    stats = buyer_request_stats(buyer_id)
    clicks = (
        db.session.query(func.count(ClickEvent.id))
        .join(Campaign, ClickEvent.campaign_id == Campaign.id)
        .filter(Campaign.buyer_id == buyer_id)
        .filter(ClickEvent.status == "ACCEPTED")
        .scalar()
        or 0
    )
    total_requests = stats["total_requests"]
    fill_rate = stats["fill_rate"]
    click_rate = clicks / total_requests if total_requests else 0
    if total_requests >= 10 and (fill_rate < 0.5 or click_rate < 0.01):
        status = "UNDER_DELIVERING"
        note = "Low fill or click rate; delivery balancing may boost exposure."
    else:
        status = "ON_TRACK"
        note = "Delivery pacing is within expected range."
    return {
        "status": status,
        "fill_rate": fill_rate,
        "total_requests": total_requests,
        "note": note,
    }


def admin_daily_metrics(days=14):
    start_date = date.today() - timedelta(days=days - 1)

    click_rows = (
        db.session.query(
            func.date(ClickEvent.ts).label("day"),
            func.count(ClickEvent.id).label("clicks"),
            func.sum(ClickEvent.spend_delta).label("spend"),
            func.sum(ClickEvent.earnings_delta).label("earnings"),
            func.sum(ClickEvent.profit_delta).label("profit"),
        )
        .filter(ClickEvent.status == "ACCEPTED")
        .filter(ClickEvent.ts >= start_date)
        .group_by("day")
        .all()
    )

    impression_rows = (
        db.session.query(
            func.date(ImpressionEvent.ts).label("day"),
            func.count(ImpressionEvent.id).label("impressions"),
        )
        .filter(ImpressionEvent.status == "ACCEPTED")
        .filter(ImpressionEvent.ts >= start_date)
        .group_by("day")
        .all()
    )

    return build_daily_series(click_rows, impression_rows, days)


def admin_top_campaigns(limit=5):
    rows = (
        db.session.query(
            Campaign.id,
            Campaign.name,
            func.sum(ClickEvent.spend_delta).label("spend"),
            func.count(ClickEvent.id).label("clicks"),
        )
        .join(ClickEvent, ClickEvent.campaign_id == Campaign.id)
        .filter(ClickEvent.status == "ACCEPTED")
        .group_by(Campaign.id, Campaign.name)
        .order_by(func.sum(ClickEvent.spend_delta).desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": row.id,
            "name": row.name,
            "spend": float(row.spend or 0),
            "clicks": int(row.clicks or 0),
        }
        for row in rows
    ]


def admin_top_partners(limit=5):
    rows = (
        db.session.query(
            User.id,
            User.email,
            func.sum(ClickEvent.earnings_delta).label("earnings"),
            func.count(ClickEvent.id).label("clicks"),
        )
        .join(ClickEvent, ClickEvent.partner_id == User.id)
        .filter(ClickEvent.status == "ACCEPTED")
        .group_by(User.id, User.email)
        .order_by(func.sum(ClickEvent.earnings_delta).desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": row.id,
            "email": row.email,
            "earnings": float(row.earnings or 0),
            "clicks": int(row.clicks or 0),
        }
        for row in rows
    ]


def partner_quality_summary(partner_id):
    accepted_clicks = (
        ClickEvent.query.filter_by(partner_id=partner_id, status="ACCEPTED").count()
    )
    rejected_clicks = (
        ClickEvent.query.filter_by(partner_id=partner_id, status="REJECTED").count()
    )
    accepted_impressions = (
        ImpressionEvent.query.filter_by(partner_id=partner_id, status="ACCEPTED").count()
    )
    earnings = (
        db.session.query(func.sum(ClickEvent.earnings_delta))
        .filter(ClickEvent.partner_id == partner_id)
        .filter(ClickEvent.status == "ACCEPTED")
        .scalar()
        or 0
    )

    total_clicks = accepted_clicks + rejected_clicks
    ctr = accepted_clicks / accepted_impressions if accepted_impressions else 0
    epc = float(earnings) / accepted_clicks if accepted_clicks else 0
    rejection_rate = rejected_clicks / total_clicks if total_clicks else 0

    quality = partner_quality_state(
        partner_id=partner_id,
        recent_days=current_app.config.get("PARTNER_QUALITY_RECENT_DAYS", 1),
        long_days=current_app.config.get("PARTNER_QUALITY_LONG_DAYS", 7),
        new_clicks_threshold=current_app.config.get("PARTNER_QUALITY_NEW_CLICKS", 10),
        risky_reject_rate=current_app.config.get("PARTNER_QUALITY_RISKY_REJECT_RATE", 0.2),
        recovering_reject_rate=current_app.config.get(
            "PARTNER_QUALITY_RECOVER_REJECT_RATE", 0.1
        ),
        delta_multipliers={
            "NEW": current_app.config.get("PARTNER_QUALITY_DELTA_NEW", 0.8),
            "STABLE": current_app.config.get("PARTNER_QUALITY_DELTA_STABLE", 1.0),
            "RISKY": current_app.config.get("PARTNER_QUALITY_DELTA_RISKY", 1.5),
            "RECOVERING": current_app.config.get("PARTNER_QUALITY_DELTA_RECOVERING", 1.1),
        },
    )
    recent_reject_rate = partner_reject_rate(
        partner_id, current_app.config.get("MATCH_REJECT_LOOKBACK_DAYS", 7)
    )

    return {
        "accepted_clicks": accepted_clicks,
        "rejected_clicks": rejected_clicks,
        "accepted_impressions": accepted_impressions,
        "ctr": ctr,
        "epc": epc,
        "rejection_rate": rejection_rate,
        "partner_quality_state": quality["state"],
        "partner_quality_note": quality["note"],
        "recent_reject_rate": recent_reject_rate,
    }


def admin_marketplace_health():
    total_requests = PartnerAdRequestEvent.query.count()
    filled_requests = PartnerAdRequestEvent.query.filter_by(filled=True).count()
    fill_rate = filled_requests / total_requests if total_requests else 0

    accepted_clicks = ClickEvent.query.filter_by(status="ACCEPTED").count()
    rejected_clicks = ClickEvent.query.filter_by(status="REJECTED").count()
    total_clicks = accepted_clicks + rejected_clicks
    reject_rate = rejected_clicks / total_clicks if total_clicks else 0

    spend = (
        db.session.query(func.sum(ClickEvent.spend_delta))
        .filter(ClickEvent.status == "ACCEPTED")
        .scalar()
        or 0
    )
    profit = (
        db.session.query(func.sum(ClickEvent.profit_delta))
        .filter(ClickEvent.status == "ACCEPTED")
        .scalar()
        or 0
    )
    take_rate = float(profit) / float(spend) if spend else 0

    buyer_rows = (
        db.session.query(User.id, User.email)
        .join(Campaign, Campaign.buyer_id == User.id)
        .filter(User.role == "buyer")
        .group_by(User.id, User.email)
        .all()
    )
    under_delivering = []
    for row in buyer_rows:
        stats = buyer_request_stats(row.id)
        delivery = buyer_delivery_status(row.id)
        under_delivering.append(
            {
                "id": row.id,
                "email": row.email,
                "fill_rate": stats["fill_rate"],
                "clicks": (
                    db.session.query(func.count(ClickEvent.id))
                    .join(Campaign, ClickEvent.campaign_id == Campaign.id)
                    .filter(Campaign.buyer_id == row.id)
                    .filter(ClickEvent.status == "ACCEPTED")
                    .scalar()
                    or 0
                ),
                "status": delivery["status"],
            }
        )

    under_delivering.sort(key=lambda item: (item["fill_rate"], item["clicks"]))

    partner_rows = User.query.filter_by(role="partner").all()
    low_quality = []
    for partner in partner_rows:
        quality = partner_quality_summary(partner.id)
        low_quality.append(
            {
                "id": partner.id,
                "email": partner.email,
                "rejection_rate": quality["rejection_rate"],
                "ctr": quality["ctr"],
            }
        )
    low_quality.sort(key=lambda item: (-item["rejection_rate"], item["ctr"]))

    snapshot = build_market_health_snapshot()
    market_note = derive_adaptive_multipliers(snapshot)["market_note"]

    return {
        "fill_rate": fill_rate,
        "reject_rate": reject_rate,
        "profit": float(profit or 0),
        "take_rate": take_rate,
        "market_note": market_note,
        "top_under_delivering_buyers": under_delivering[:5],
        "top_low_quality_partners": low_quality[:5],
    }


def admin_risk_summary():
    accepted = ClickEvent.query.filter_by(status="ACCEPTED").count()
    rejected = ClickEvent.query.filter_by(status="REJECTED").count()
    total = accepted + rejected
    rejection_rate = rejected / total if total else 0

    reason_rows = (
        db.session.query(ClickEvent.reject_reason, func.count(ClickEvent.id).label("count"))
        .filter(ClickEvent.status == "REJECTED")
        .group_by(ClickEvent.reject_reason)
        .order_by(func.count(ClickEvent.id).desc())
        .all()
    )

    top_reasons = [
        {"reason": row.reject_reason or "UNKNOWN", "count": int(row.count or 0)}
        for row in reason_rows
    ]

    return {
        "totals": {
            "accepted": accepted,
            "rejected": rejected,
            "total": total,
            "rejection_rate": rejection_rate,
        },
        "top_reasons": top_reasons,
    }


def admin_risk_series(start_date, end_date):
    rows = (
        db.session.query(
            func.date(ClickEvent.ts).label("day"),
            func.sum(case((ClickEvent.status == "ACCEPTED", 1), else_=0)).label(
                "accepted"
            ),
            func.sum(case((ClickEvent.status == "REJECTED", 1), else_=0)).label(
                "rejected"
            ),
        )
        .filter(func.date(ClickEvent.ts) >= start_date)
        .filter(func.date(ClickEvent.ts) <= end_date)
        .group_by("day")
        .all()
    )

    return build_risk_series(rows, start_date, end_date)


def admin_risk_top_partners(limit=5):
    rows = (
        db.session.query(
            User.id,
            User.email,
            func.sum(case((ClickEvent.status == "REJECTED", 1), else_=0)).label(
                "rejected"
            ),
            func.count(ClickEvent.id).label("total"),
        )
        .join(ClickEvent, ClickEvent.partner_id == User.id)
        .group_by(User.id, User.email)
        .order_by(func.sum(case((ClickEvent.status == "REJECTED", 1), else_=0)).desc())
        .limit(limit)
        .all()
    )

    results = []
    for row in rows:
        total = int(row.total or 0)
        rejected = int(row.rejected or 0)
        rate = rejected / total if total else 0
        results.append(
            {
                "id": row.id,
                "email": row.email,
                "rejected": rejected,
                "total": total,
                "rejection_rate": rate,
            }
        )

    return results
