from datetime import date, timedelta

from sqlalchemy import case, func

from app.extensions import db
from app.models.campaign import Campaign
from app.models.click_event import ClickEvent
from app.models.impression_event import ImpressionEvent
from app.models.user import User


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

    return {
        "accepted_clicks": accepted_clicks,
        "rejected_clicks": rejected_clicks,
        "accepted_impressions": accepted_impressions,
        "ctr": ctr,
        "epc": epc,
        "rejection_rate": rejection_rate,
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
