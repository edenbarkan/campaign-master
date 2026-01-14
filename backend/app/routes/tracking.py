from datetime import datetime, timedelta
from decimal import Decimal

from flask import Blueprint, current_app, jsonify, redirect, request

from app.extensions import db
from app.models.assignment import AdAssignment
from app.models.campaign import Campaign
from app.models.click_event import ClickEvent
from app.models.impression_event import ImpressionEvent
from app.services.validation import build_request_fingerprint, validate_click

tracking_bp = Blueprint("tracking", __name__)


@tracking_bp.route("/api/track/impression", methods=["POST"])
def track_impression():
    code = (request.args.get("code") or "").strip()
    if not code:
        return jsonify({"error": "missing_code"}), 400

    assignment = AdAssignment.query.filter_by(code=code).first()
    if not assignment:
        return jsonify({"error": "not_found"}), 404
    ip_hash, _, _ = build_request_fingerprint(request)
    dedup_seconds = current_app.config.get("IMPRESSION_DEDUP_WINDOW_SECONDS", 60)
    cutoff = datetime.utcnow() - timedelta(seconds=dedup_seconds)

    recent = (
        ImpressionEvent.query.filter_by(assignment_code=assignment.code, ip_hash=ip_hash)
        .filter(ImpressionEvent.ts >= cutoff)
        .first()
    )

    status = "DEDUPED" if recent else "ACCEPTED"
    dedup_reason = "DUPLICATE_WINDOW" if recent else None

    event = ImpressionEvent(
        assignment_code=assignment.code,
        campaign_id=assignment.campaign_id,
        ad_id=assignment.ad_id,
        partner_id=assignment.partner_id,
        ip_hash=ip_hash,
        status=status,
        dedup_reason=dedup_reason,
    )
    db.session.add(event)
    db.session.commit()

    return jsonify({"status": "ok", "deduped": status == "DEDUPED"})


@tracking_bp.route("/t/<code>", methods=["GET"])
def track_click(code):
    assignment = AdAssignment.query.filter_by(code=code).first()
    decision = validate_click(assignment)

    destination_url = "/"
    if assignment and assignment.ad:
        destination_url = assignment.ad.destination_url

    if decision.status == "REJECTED":
        event = ClickEvent(
            assignment_code=code,
            partner_id=assignment.partner_id if assignment else None,
            campaign_id=assignment.campaign_id if assignment else None,
            ad_id=assignment.ad_id if assignment else None,
            ip_hash=decision.ip_hash,
            ua_hash=decision.ua_hash,
            status="REJECTED",
            reject_reason=decision.reason,
        )
        db.session.add(event)
        db.session.commit()
        return redirect(destination_url, code=302)

    campaign = (
        db.session.query(Campaign)
        .filter(Campaign.id == assignment.campaign_id)
        .with_for_update()
        .first()
    )

    if not campaign:
        status = "REJECTED"
        reject_reason = "INVALID_ASSIGNMENT"
        spend_delta = Decimal("0")
        earnings_delta = Decimal("0")
        profit_delta = Decimal("0")
    else:
        budget_remaining = campaign.budget_remaining
        if campaign.status != "active" or budget_remaining < campaign.buyer_cpc:
            if campaign.status == "active" and budget_remaining < campaign.buyer_cpc:
                campaign.status = "paused"
            status = "REJECTED"
            reject_reason = "BUDGET_EXHAUSTED"
            spend_delta = Decimal("0")
            earnings_delta = Decimal("0")
            profit_delta = Decimal("0")
        else:
            spend_delta = campaign.buyer_cpc
            earnings_delta = campaign.partner_payout
            profit_delta = campaign.buyer_cpc - campaign.partner_payout
            campaign.budget_spent = (campaign.budget_spent or Decimal("0")) + spend_delta
            if campaign.budget_remaining < campaign.buyer_cpc:
                campaign.status = "paused"
            status = "ACCEPTED"
            reject_reason = None

    event = ClickEvent(
        assignment_code=assignment.code,
        partner_id=assignment.partner_id,
        campaign_id=assignment.campaign_id,
        ad_id=assignment.ad_id,
        ip_hash=decision.ip_hash,
        ua_hash=decision.ua_hash,
        status=status,
        reject_reason=reject_reason,
        spend_delta=spend_delta,
        earnings_delta=earnings_delta,
        profit_delta=profit_delta,
    )
    db.session.add(event)
    db.session.commit()

    return redirect(destination_url, code=302)
