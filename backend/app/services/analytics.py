from datetime import date, timedelta

from sqlalchemy import case, func

from app.extensions import db
from app.models.campaign import Campaign
from app.models.tracking_event import TrackingEvent
from app.models.user import User


def build_daily_series(rows, days):
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)
    row_map = {row.day: row for row in rows}
    series = []

    for offset in range(days):
        current_day = start_date + timedelta(days=offset)
        row = row_map.get(current_day)
        series.append(
            {
                "date": current_day.isoformat(),
                "spend": float(getattr(row, "spend", 0) or 0),
                "earnings": float(getattr(row, "earnings", 0) or 0),
                "clicks": int(getattr(row, "clicks", 0) or 0),
                "impressions": int(getattr(row, "impressions", 0) or 0),
            }
        )

    return series


def buyer_daily_metrics(buyer_id, days=14):
    start_date = date.today() - timedelta(days=days - 1)

    rows = (
        db.session.query(
            func.date(TrackingEvent.created_at).label("day"),
            func.sum(
                case((TrackingEvent.event_type == "click", 1), else_=0)
            ).label("clicks"),
            func.sum(
                case((TrackingEvent.event_type == "impression", 1), else_=0)
            ).label("impressions"),
            func.sum(
                case((TrackingEvent.event_type == "click", Campaign.buyer_cpc), else_=0)
            ).label("spend"),
        )
        .join(Campaign, TrackingEvent.campaign_id == Campaign.id)
        .filter(Campaign.buyer_id == buyer_id)
        .filter(TrackingEvent.created_at >= start_date)
        .group_by("day")
        .all()
    )

    return build_daily_series(rows, days)


def partner_daily_metrics(partner_id, days=14):
    start_date = date.today() - timedelta(days=days - 1)

    rows = (
        db.session.query(
            func.date(TrackingEvent.created_at).label("day"),
            func.sum(
                case((TrackingEvent.event_type == "click", 1), else_=0)
            ).label("clicks"),
            func.sum(
                case((TrackingEvent.event_type == "impression", 1), else_=0)
            ).label("impressions"),
            func.sum(
                case(
                    (TrackingEvent.event_type == "click", Campaign.partner_payout),
                    else_=0,
                )
            ).label("earnings"),
        )
        .join(Campaign, TrackingEvent.campaign_id == Campaign.id)
        .filter(TrackingEvent.partner_id == partner_id)
        .filter(TrackingEvent.created_at >= start_date)
        .group_by("day")
        .all()
    )

    return build_daily_series(rows, days)


def buyer_campaign_table(buyer_id):
    campaigns = Campaign.query.filter_by(buyer_id=buyer_id).order_by(Campaign.id.desc()).all()
    results = []

    for campaign in campaigns:
        click_count = (
            TrackingEvent.query.filter_by(campaign_id=campaign.id, event_type="click").count()
        )
        spend = float(campaign.buyer_cpc) * click_count

        partner_rows = (
            db.session.query(
                User.id,
                User.email,
                func.count(TrackingEvent.id).label("clicks"),
            )
            .join(TrackingEvent, TrackingEvent.partner_id == User.id)
            .filter(
                TrackingEvent.campaign_id == campaign.id,
                TrackingEvent.event_type == "click",
            )
            .group_by(User.id, User.email)
            .order_by(func.count(TrackingEvent.id).desc())
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
            func.count(TrackingEvent.id).label("clicks"),
            func.sum(Campaign.partner_payout).label("earnings"),
        )
        .join(Campaign, TrackingEvent.campaign_id == Campaign.id)
        .filter(TrackingEvent.partner_id == partner_id)
        .filter(TrackingEvent.event_type == "click")
        .group_by(Campaign.id, Campaign.name)
        .order_by(func.sum(Campaign.partner_payout).desc())
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
