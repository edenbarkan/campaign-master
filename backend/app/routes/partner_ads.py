import secrets

import json

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity

from app.auth.decorators import roles_required
from app.extensions import db
from app.models.partner_ad_exposure import PartnerAdExposure
from app.models.partner_ad_request_event import PartnerAdRequestEvent
from app.models.assignment import AdAssignment
from app.services.matching import select_ad_for_partner

partner_ads_bp = Blueprint("partner_ads", __name__)


def generate_code():
    while True:
        code = secrets.token_urlsafe(8).rstrip("=")
        if not AdAssignment.query.filter_by(code=code).first():
            return code


def ad_payload(ad, campaign, assignment, explanation, score_breakdown):
    return {
        "filled": True,
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
        "explanation": explanation,
        "score_breakdown": score_breakdown,
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

    # Optional debug mode returns top candidate breakdowns for QA only.
    result = select_ad_for_partner(
        partner_id,
        category=category,
        geo=geo,
        device=device,
        placement=placement,
        freq_cap_seconds=current_app.config.get("FREQ_CAP_SECONDS", 60),
        ctr_lookback_days=current_app.config.get("MATCH_CTR_LOOKBACK_DAYS", 14),
        reject_lookback_days=current_app.config.get("MATCH_REJECT_LOOKBACK_DAYS", 7),
        ctr_weight=current_app.config.get("MATCH_CTR_WEIGHT", 1.0),
        targeting_bonus_value=current_app.config.get("MATCH_TARGETING_BONUS", 0.5),
        reject_penalty_weight=current_app.config.get("MATCH_REJECT_PENALTY_WEIGHT", 1.0),
        exploration_rate=current_app.config.get("EXPLORATION_RATE", 0.05),
        exploration_bonus=current_app.config.get("EXPLORATION_BONUS", 0.2),
        exploration_new_partner_requests=current_app.config.get(
            "EXPLORATION_NEW_PARTNER_REQUESTS", 5
        ),
        exploration_new_ad_serves=current_app.config.get("EXPLORATION_NEW_AD_SERVES", 1),
        exploration_max_ad_serves=current_app.config.get("EXPLORATION_MAX_AD_SERVES", 5),
        exploration_lookback_days=current_app.config.get("EXPLORATION_LOOKBACK_DAYS", 7),
        quality_recent_days=current_app.config.get("PARTNER_QUALITY_RECENT_DAYS", 1),
        quality_long_days=current_app.config.get("PARTNER_QUALITY_LONG_DAYS", 7),
        quality_new_clicks=current_app.config.get("PARTNER_QUALITY_NEW_CLICKS", 10),
        quality_risky_reject_rate=current_app.config.get(
            "PARTNER_QUALITY_RISKY_REJECT_RATE", 0.2
        ),
        quality_recover_reject_rate=current_app.config.get(
            "PARTNER_QUALITY_RECOVER_REJECT_RATE", 0.1
        ),
        quality_delta_new=current_app.config.get("PARTNER_QUALITY_DELTA_NEW", 0.8),
        quality_delta_stable=current_app.config.get("PARTNER_QUALITY_DELTA_STABLE", 1.0),
        quality_delta_risky=current_app.config.get("PARTNER_QUALITY_DELTA_RISKY", 1.5),
        quality_delta_recovering=current_app.config.get(
            "PARTNER_QUALITY_DELTA_RECOVERING", 1.1
        ),
        delivery_lookback_days=current_app.config.get("DELIVERY_LOOKBACK_DAYS", 7),
        delivery_min_requests=current_app.config.get("DELIVERY_MIN_REQUESTS", 10),
        delivery_low_click_rate=current_app.config.get("DELIVERY_LOW_CLICK_RATE", 0.01),
        delivery_min_budget_remaining_ratio=current_app.config.get(
            "DELIVERY_MIN_BUDGET_REMAINING_RATIO", 0.5
        ),
        delivery_boost_value=current_app.config.get("DELIVERY_BOOST_VALUE", 0.2),
        debug=str(current_app.config.get("MATCHING_DEBUG", "0")).lower()
        in ("1", "true", "yes"),
        debug_limit=3,
    )
    if not result.ad or not result.campaign:
        request_event = PartnerAdRequestEvent(
            partner_id=partner_id,
            placement=placement,
            device=device,
            geo=geo,
            category=category,
            filled=False,
        )
        db.session.add(request_event)
        db.session.commit()
        response = {"filled": False, "reason": result.unfilled_reason}
        if result.debug_candidates is not None:
            response["debug_candidates"] = result.debug_candidates
        return jsonify(response), 200

    ad = result.ad
    campaign = result.campaign

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

    exposure = PartnerAdExposure.query.filter_by(partner_id=partner_id, ad_id=ad.id).first()
    if exposure:
        exposure.last_served_at = db.func.now()
    else:
        db.session.add(
            PartnerAdExposure(
                partner_id=partner_id,
                ad_id=ad.id,
            )
        )

    request_event = PartnerAdRequestEvent(
        partner_id=partner_id,
        placement=placement,
        device=device,
        geo=geo,
        category=category,
        filled=True,
        ad_id=ad.id,
        campaign_id=campaign.id,
        assignment_code=assignment.code,
        explanation=result.explanation,
        score_breakdown=json.dumps(result.score_breakdown),
    )
    db.session.add(request_event)
    db.session.commit()

    response = ad_payload(ad, campaign, assignment, result.explanation, result.score_breakdown)
    if result.debug_candidates is not None:
        response["debug_candidates"] = result.debug_candidates
    return jsonify(response)
