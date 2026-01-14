from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from app.auth.decorators import roles_required
from app.extensions import db
from app.models.ad import Ad
from app.models.campaign import Campaign

buyer_ads_bp = Blueprint("buyer_ads", __name__)


def ad_to_dict(ad):
    return {
        "id": ad.id,
        "campaign_id": ad.campaign_id,
        "title": ad.title,
        "body": ad.body,
        "image_url": ad.image_url,
        "destination_url": ad.destination_url,
        "active": ad.active,
    }


def get_campaign_for_buyer(campaign_id, buyer_id):
    return Campaign.query.filter_by(id=campaign_id, buyer_id=buyer_id).first()


@buyer_ads_bp.route("/api/buyer/campaigns/<int:campaign_id>/ads", methods=["GET"])
@roles_required("buyer")
def list_ads(campaign_id):
    try:
        buyer_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_identity"}), 401

    campaign = get_campaign_for_buyer(campaign_id, buyer_id)
    if not campaign:
        return jsonify({"error": "not_found"}), 404

    limit = request.args.get("limit", 50)
    offset = request.args.get("offset", 0)
    try:
        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_pagination"}), 400

    base_query = Ad.query.filter_by(campaign_id=campaign.id)
    total = base_query.count()
    ads = base_query.order_by(Ad.id.desc()).limit(limit).offset(offset).all()
    return jsonify(
        {
            "ads": [ad_to_dict(ad) for ad in ads],
            "meta": {"limit": limit, "offset": offset, "total": total},
        }
    )


@buyer_ads_bp.route("/api/buyer/campaigns/<int:campaign_id>/ads", methods=["POST"])
@roles_required("buyer")
def create_ad(campaign_id):
    try:
        buyer_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_identity"}), 401

    campaign = get_campaign_for_buyer(campaign_id, buyer_id)
    if not campaign:
        return jsonify({"error": "not_found"}), 404

    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()
    body = (payload.get("body") or "").strip()
    image_url = (payload.get("image_url") or "").strip()
    destination_url = (payload.get("destination_url") or "").strip()
    active = payload.get("active")
    active = bool(active) if active is not None else True

    if not title or not body or not image_url or not destination_url:
        return jsonify({"error": "invalid_payload"}), 400

    ad = Ad(
        campaign_id=campaign.id,
        title=title,
        body=body,
        image_url=image_url,
        destination_url=destination_url,
        active=active,
    )
    db.session.add(ad)
    db.session.commit()

    return jsonify({"ad": ad_to_dict(ad)}), 201


@buyer_ads_bp.route(
    "/api/buyer/campaigns/<int:campaign_id>/ads/<int:ad_id>", methods=["PUT"]
)
@roles_required("buyer")
def update_ad(campaign_id, ad_id):
    try:
        buyer_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_identity"}), 401

    campaign = get_campaign_for_buyer(campaign_id, buyer_id)
    if not campaign:
        return jsonify({"error": "not_found"}), 404

    ad = Ad.query.filter_by(id=ad_id, campaign_id=campaign.id).first()
    if not ad:
        return jsonify({"error": "not_found"}), 404

    payload = request.get_json(silent=True) or {}

    if "title" in payload:
        title = (payload.get("title") or "").strip()
        if not title:
            return jsonify({"error": "invalid_title"}), 400
        ad.title = title

    if "body" in payload:
        body = (payload.get("body") or "").strip()
        if not body:
            return jsonify({"error": "invalid_body"}), 400
        ad.body = body

    if "image_url" in payload:
        image_url = (payload.get("image_url") or "").strip()
        if not image_url:
            return jsonify({"error": "invalid_image_url"}), 400
        ad.image_url = image_url

    if "destination_url" in payload:
        destination_url = (payload.get("destination_url") or "").strip()
        if not destination_url:
            return jsonify({"error": "invalid_destination_url"}), 400
        ad.destination_url = destination_url

    if "active" in payload:
        ad.active = bool(payload.get("active"))

    db.session.commit()
    return jsonify({"ad": ad_to_dict(ad)})
