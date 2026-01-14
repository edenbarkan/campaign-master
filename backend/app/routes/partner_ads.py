import secrets

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from app.auth.decorators import roles_required
from app.extensions import db
from app.models.assignment import AdAssignment
from app.services.matching import select_ad_for_partner

partner_ads_bp = Blueprint("partner_ads", __name__)


def generate_code():
    while True:
        code = secrets.token_urlsafe(8).rstrip("=")
        if not AdAssignment.query.filter_by(code=code).first():
            return code


def ad_payload(ad, campaign, assignment):
    return {
        "assignment_code": assignment.code,
        "tracking_url": f"/t/{assignment.code}",
        "campaign": {
            "id": campaign.id,
            "max_cpc": float(campaign.max_cpc),
            "partner_payout": float(campaign.partner_payout),
        },
        "ad": {
            "id": ad.id,
            "title": ad.title,
            "body": ad.body,
            "image_url": ad.image_url,
            "destination_url": ad.destination_url,
        },
    }


@partner_ads_bp.route("/api/partner/ad", methods=["GET"])
@roles_required("partner")
def request_ad():
    try:
        partner_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_identity"}), 401

    category = (request.args.get("category") or "").strip() or None
    geo = (request.args.get("geo") or "").strip() or None
    placement = (request.args.get("placement") or "").strip() or None
    device = (request.args.get("device") or "").strip() or None

    ad, campaign = select_ad_for_partner(
        partner_id, category=category, geo=geo, device=device, placement=placement
    )
    if not ad or not campaign:
        return jsonify({"error": "no_fill"}), 404

    assignment = AdAssignment(
        code=generate_code(),
        partner_id=partner_id,
        campaign_id=campaign.id,
        ad_id=ad.id,
        category=category,
        geo=geo,
        placement=placement,
        device=device,
    )
    db.session.add(assignment)
    db.session.commit()

    return jsonify(ad_payload(ad, campaign, assignment))
