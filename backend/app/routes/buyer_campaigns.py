from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from app.auth.decorators import roles_required
from app.extensions import db
from app.models.campaign import Campaign
from app.models.click_event import ClickEvent
from app.models.impression_event import ImpressionEvent
from app.services.pricing import compute_partner_payout, get_platform_fee_percent

buyer_campaigns_bp = Blueprint("buyer_campaigns", __name__)

ALLOWED_STATUSES = {"active", "paused"}


def parse_decimal(value, field_name):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"invalid_{field_name}")


def parse_date(value, field_name):
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"invalid_{field_name}")


def campaign_delivery_status(campaign):
    clicks = (
        ClickEvent.query.filter_by(campaign_id=campaign.id, status="ACCEPTED").count()
    )
    impressions = (
        ImpressionEvent.query.filter_by(campaign_id=campaign.id, status="ACCEPTED").count()
    )
    ctr = clicks / impressions if impressions else 0
    if campaign.status != "active":
        return "PAUSED", ctr
    if impressions >= 20 and ctr < 0.01:
        return "UNDER_DELIVERING", ctr
    return "ON_TRACK", ctr


def campaign_to_dict(campaign):
    delivery_status, ctr = campaign_delivery_status(campaign)
    return {
        "id": campaign.id,
        "name": campaign.name,
        "status": campaign.status,
        "budget_total": float(campaign.budget_total),
        "budget_spent": float(campaign.budget_spent),
        "budget_remaining": float(campaign.budget_remaining),
        "buyer_cpc": float(campaign.buyer_cpc),
        "max_cpc": float(campaign.max_cpc),
        "partner_payout": float(campaign.partner_payout),
        "platform_fee_percent": float(get_platform_fee_percent()),
        "delivery_status": delivery_status,
        "ctr": ctr,
        "targeting": {
            "category": campaign.targeting_category,
            "geo": campaign.targeting_geo,
            "device": campaign.targeting_device,
            "placement": campaign.targeting_placement,
        },
        "start_date": campaign.start_date.isoformat() if campaign.start_date else None,
        "end_date": campaign.end_date.isoformat() if campaign.end_date else None,
    }


@buyer_campaigns_bp.route("/api/buyer/campaigns", methods=["GET"])
@roles_required("buyer")
def list_campaigns():
    try:
        buyer_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_identity"}), 401
    limit = request.args.get("limit", 50)
    offset = request.args.get("offset", 0)
    try:
        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_pagination"}), 400

    base_query = Campaign.query.filter_by(buyer_id=buyer_id)
    total = base_query.count()
    campaigns = (
        base_query.order_by(Campaign.id.desc()).limit(limit).offset(offset).all()
    )
    return jsonify(
        {
            "campaigns": [campaign_to_dict(c) for c in campaigns],
            "meta": {
                "limit": limit,
                "offset": offset,
                "total": total,
                "platform_fee_percent": float(get_platform_fee_percent()),
            },
        }
    )


@buyer_campaigns_bp.route("/api/buyer/campaigns", methods=["POST"])
@roles_required("buyer")
def create_campaign():
    try:
        buyer_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_identity"}), 401
    payload = request.get_json(silent=True) or {}

    name = (payload.get("name") or "").strip()
    status = (payload.get("status") or "active").strip().lower()

    if not name or status not in ALLOWED_STATUSES:
        return jsonify({"error": "invalid_payload"}), 400

    try:
        budget_total = parse_decimal(payload.get("budget_total"), "budget_total")
        max_cpc_value = payload.get("max_cpc", payload.get("buyer_cpc"))
        max_cpc = parse_decimal(max_cpc_value, "max_cpc")
        start_date = parse_date(payload.get("start_date"), "start_date")
        end_date = parse_date(payload.get("end_date"), "end_date")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if budget_total <= 0 or max_cpc <= 0:
        return jsonify({"error": "invalid_pricing"}), 400

    partner_payout = compute_partner_payout(max_cpc)

    campaign = Campaign(
        buyer_id=buyer_id,
        name=name,
        status=status,
        budget_total=budget_total,
        buyer_cpc=max_cpc,
        partner_payout=partner_payout,
        targeting_category=(payload.get("targeting", {}) or {}).get("category"),
        targeting_geo=(payload.get("targeting", {}) or {}).get("geo"),
        targeting_device=(payload.get("targeting", {}) or {}).get("device"),
        targeting_placement=(payload.get("targeting", {}) or {}).get("placement"),
        start_date=start_date,
        end_date=end_date,
    )
    db.session.add(campaign)
    db.session.commit()

    return jsonify({"campaign": campaign_to_dict(campaign)}), 201


@buyer_campaigns_bp.route("/api/buyer/campaigns/<int:campaign_id>", methods=["GET"])
@roles_required("buyer")
def get_campaign(campaign_id):
    try:
        buyer_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_identity"}), 401
    campaign = Campaign.query.filter_by(id=campaign_id, buyer_id=buyer_id).first()
    if not campaign:
        return jsonify({"error": "not_found"}), 404
    return jsonify({"campaign": campaign_to_dict(campaign)})


@buyer_campaigns_bp.route("/api/buyer/campaigns/<int:campaign_id>", methods=["PUT"])
@roles_required("buyer")
def update_campaign(campaign_id):
    try:
        buyer_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_identity"}), 401
    campaign = Campaign.query.filter_by(id=campaign_id, buyer_id=buyer_id).first()
    if not campaign:
        return jsonify({"error": "not_found"}), 404

    payload = request.get_json(silent=True) or {}

    if "name" in payload:
        name = (payload.get("name") or "").strip()
        if not name:
            return jsonify({"error": "invalid_name"}), 400
        campaign.name = name

    if "status" in payload:
        status = (payload.get("status") or "").strip().lower()
        if status not in ALLOWED_STATUSES:
            return jsonify({"error": "invalid_status"}), 400
        campaign.status = status

    if "budget_total" in payload:
        try:
            budget_total = parse_decimal(payload.get("budget_total"), "budget_total")
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        if budget_total <= 0:
            return jsonify({"error": "invalid_budget_total"}), 400
        campaign.budget_total = budget_total

    if "buyer_cpc" in payload or "max_cpc" in payload:
        try:
            max_cpc_value = payload.get("max_cpc", payload.get("buyer_cpc"))
            buyer_cpc = parse_decimal(max_cpc_value, "max_cpc")
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        if buyer_cpc <= 0:
            return jsonify({"error": "invalid_buyer_cpc"}), 400
        campaign.buyer_cpc = buyer_cpc

    campaign.partner_payout = compute_partner_payout(campaign.buyer_cpc)

    if "targeting" in payload:
        targeting = payload.get("targeting") or {}
        campaign.targeting_category = targeting.get("category")
        campaign.targeting_geo = targeting.get("geo")
        campaign.targeting_device = targeting.get("device")
        campaign.targeting_placement = targeting.get("placement")

    if "start_date" in payload:
        try:
            campaign.start_date = parse_date(payload.get("start_date"), "start_date")
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    if "end_date" in payload:
        try:
            campaign.end_date = parse_date(payload.get("end_date"), "end_date")
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    db.session.commit()
    return jsonify({"campaign": campaign_to_dict(campaign)})
