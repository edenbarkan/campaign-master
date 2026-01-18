from datetime import date, timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from app.auth.decorators import roles_required
from app.services.analytics import (
    admin_risk_series,
    admin_risk_summary,
    admin_risk_top_partners,
    admin_daily_metrics,
    admin_marketplace_health,
    admin_top_campaigns,
    admin_top_partners,
    buyer_delivery_status,
    buyer_campaign_table,
    buyer_daily_metrics,
    partner_campaign_table,
    partner_daily_metrics,
    partner_latest_request,
    partner_request_stats,
    partner_top_ads,
    partner_quality_summary,
)

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/api/buyer/analytics/summary", methods=["GET"])
@roles_required("buyer")
def buyer_summary():
    try:
        buyer_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_identity"}), 401

    daily = buyer_daily_metrics(buyer_id)
    spend_total = sum(item["spend"] for item in daily)
    clicks_total = sum(item["clicks"] for item in daily)
    impressions_total = sum(item["impressions"] for item in daily)

    effective_cpc = spend_total / clicks_total if clicks_total else 0
    cost_efficiency = clicks_total / spend_total if spend_total else 0

    return jsonify(
        {
            "daily": daily,
            "totals": {
                "spend": spend_total,
                "clicks": clicks_total,
                "impressions": impressions_total,
                "effective_cpc": effective_cpc,
                "cost_efficiency": cost_efficiency,
            },
            "campaigns": buyer_campaign_table(buyer_id),
            "delivery_status": buyer_delivery_status(buyer_id),
        }
    )


@analytics_bp.route("/api/partner/analytics/summary", methods=["GET"])
@roles_required("partner")
def partner_summary():
    try:
        partner_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_identity"}), 401

    daily = partner_daily_metrics(partner_id)
    earnings_total = sum(item["earnings"] for item in daily)
    accepted_clicks = sum(item["clicks"] for item in daily)
    accepted_impressions = sum(item["impressions"] for item in daily)
    epc = earnings_total / accepted_clicks if accepted_clicks else 0
    ctr = accepted_clicks / accepted_impressions if accepted_impressions else 0
    request_stats = partner_request_stats(partner_id)

    return jsonify(
        {
            "daily": daily,
            "totals": {
                "earnings": earnings_total,
                "clicks": accepted_clicks,
                "accepted_clicks": accepted_clicks,
                "accepted_impressions": accepted_impressions,
                "impressions": accepted_impressions,
                "ctr": ctr,
                "epc": epc,
            },
            "campaigns": partner_campaign_table(partner_id),
            "fill_rate": request_stats["fill_rate"],
            "unfilled_requests": request_stats["unfilled_requests"],
            "total_requests": request_stats["total_requests"],
            "filled_requests": request_stats["filled_requests"],
            "top_ads": partner_top_ads(partner_id),
            "latest_request": partner_latest_request(partner_id),
        }
    )


@analytics_bp.route("/api/partner/quality/summary", methods=["GET"])
@roles_required("partner")
def partner_quality():
    try:
        partner_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_identity"}), 401

    return jsonify(partner_quality_summary(partner_id))


@analytics_bp.route("/api/admin/analytics/summary", methods=["GET"])
@roles_required("admin")
def admin_summary():
    daily = admin_daily_metrics()
    spend_total = sum(item["spend"] for item in daily)
    earnings_total = sum(item["earnings"] for item in daily)
    profit_total = sum(item["profit"] for item in daily)
    clicks_total = sum(item["clicks"] for item in daily)
    impressions_total = sum(item["impressions"] for item in daily)

    return jsonify(
        {
            "totals": {
                "spend": spend_total,
                "earnings": earnings_total,
                "profit": profit_total,
                "clicks": clicks_total,
                "impressions": impressions_total,
            },
            "top_campaigns": admin_top_campaigns(),
            "top_partners": admin_top_partners(),
            "marketplace_health": admin_marketplace_health(),
        }
    )


@analytics_bp.route("/api/admin/analytics/series", methods=["GET"])
@roles_required("admin")
def admin_series():
    days = request.args.get("days", 14)
    try:
        days = max(1, min(int(days), 60))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_days"}), 400

    return jsonify({"daily": admin_daily_metrics(days=days)})


@analytics_bp.route("/api/admin/risk/summary", methods=["GET"])
@roles_required("admin")
def admin_risk_summary_view():
    return jsonify(admin_risk_summary())


@analytics_bp.route("/api/admin/risk/series", methods=["GET"])
@roles_required("admin")
def admin_risk_series_view():
    from_value = request.args.get("from")
    to_value = request.args.get("to")
    group_by = (request.args.get("groupBy") or "day").lower()
    if group_by != "day":
        return jsonify({"error": "invalid_group_by"}), 400

    if from_value:
        try:
            start_date = date.fromisoformat(from_value)
        except (TypeError, ValueError):
            return jsonify({"error": "invalid_from"}), 400
    else:
        start_date = date.today() - timedelta(days=13)

    if to_value:
        try:
            end_date = date.fromisoformat(to_value)
        except (TypeError, ValueError):
            return jsonify({"error": "invalid_to"}), 400
    else:
        end_date = date.today()

    if end_date < start_date:
        return jsonify({"error": "invalid_range"}), 400

    return jsonify({"daily": admin_risk_series(start_date, end_date)})


@analytics_bp.route("/api/admin/risk/top-partners", methods=["GET"])
@roles_required("admin")
def admin_risk_top_partners_view():
    limit = request.args.get("limit", 5)
    try:
        limit = max(1, min(int(limit), 50))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_limit"}), 400
    return jsonify({"partners": admin_risk_top_partners(limit=limit)})
