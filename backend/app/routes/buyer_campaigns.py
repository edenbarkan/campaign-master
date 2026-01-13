from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from app.auth.decorators import roles_required
from app.extensions import db
from app.models.campaign import Campaign

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


def campaign_to_dict(campaign):
    return {
        "id": campaign.id,
        "name": campaign.name,
        "status": campaign.status,
        "budget_total": float(campaign.budget_total),
        "budget_spent": float(campaign.budget_spent),
        "budget_remaining": float(campaign.budget_remaining),
        "buyer_cpc": float(campaign.buyer_cpc),
        "partner_payout": float(campaign.partner_payout),
        "targeting": {
            "category": campaign.targeting_category,
            "geo": campaign.targeting_geo,
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
    campaigns = Campaign.query.filter_by(buyer_id=buyer_id).order_by(Campaign.id.desc()).all()
    return jsonify({"campaigns": [campaign_to_dict(c) for c in campaigns]})


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
        buyer_cpc = parse_decimal(payload.get("buyer_cpc"), "buyer_cpc")
        partner_payout = parse_decimal(payload.get("partner_payout"), "partner_payout")
        start_date = parse_date(payload.get("start_date"), "start_date")
        end_date = parse_date(payload.get("end_date"), "end_date")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if budget_total <= 0 or buyer_cpc <= 0 or partner_payout < 0:
        return jsonify({"error": "invalid_pricing"}), 400

    if buyer_cpc < partner_payout:
        return jsonify({"error": "margin_negative"}), 400

    campaign = Campaign(
        buyer_id=buyer_id,
        name=name,
        status=status,
        budget_total=budget_total,
        buyer_cpc=buyer_cpc,
        partner_payout=partner_payout,
        targeting_category=(payload.get("targeting", {}) or {}).get("category"),
        targeting_geo=(payload.get("targeting", {}) or {}).get("geo"),
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

    if "buyer_cpc" in payload:
        try:
            buyer_cpc = parse_decimal(payload.get("buyer_cpc"), "buyer_cpc")
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        if buyer_cpc <= 0:
            return jsonify({"error": "invalid_buyer_cpc"}), 400
        campaign.buyer_cpc = buyer_cpc

    if "partner_payout" in payload:
        try:
            partner_payout = parse_decimal(payload.get("partner_payout"), "partner_payout")
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        if partner_payout < 0:
            return jsonify({"error": "invalid_partner_payout"}), 400
        campaign.partner_payout = partner_payout

    if campaign.buyer_cpc < campaign.partner_payout:
        return jsonify({"error": "margin_negative"}), 400

    if "targeting" in payload:
        targeting = payload.get("targeting") or {}
        campaign.targeting_category = targeting.get("category")
        campaign.targeting_geo = targeting.get("geo")

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
