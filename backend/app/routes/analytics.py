from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity

from app.auth.decorators import roles_required
from app.services.analytics import (
    buyer_campaign_table,
    buyer_daily_metrics,
    partner_campaign_table,
    partner_daily_metrics,
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
    clicks_total = sum(item["clicks"] for item in daily)
    impressions_total = sum(item["impressions"] for item in daily)

    epc = earnings_total / clicks_total if clicks_total else 0

    return jsonify(
        {
            "daily": daily,
            "totals": {
                "earnings": earnings_total,
                "clicks": clicks_total,
                "impressions": impressions_total,
                "epc": epc,
            },
            "campaigns": partner_campaign_table(partner_id),
        }
    )
