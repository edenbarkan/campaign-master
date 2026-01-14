from datetime import datetime
from decimal import Decimal

from flask import Blueprint, jsonify, redirect, request

from app.extensions import db
from app.models.assignment import AdAssignment
from app.models.campaign import Campaign
from app.models.tracking_event import TrackingEvent

tracking_bp = Blueprint("tracking", __name__)


@tracking_bp.route("/api/track/impression", methods=["POST"])
def track_impression():
    code = (request.args.get("code") or "").strip()
    if not code:
        return jsonify({"error": "missing_code"}), 400

    assignment = AdAssignment.query.filter_by(code=code).first()
    if not assignment:
        return jsonify({"error": "not_found"}), 404

    event = TrackingEvent(
        assignment_id=assignment.id,
        campaign_id=assignment.campaign_id,
        ad_id=assignment.ad_id,
        partner_id=assignment.partner_id,
        event_type="impression",
        created_at=datetime.utcnow(),
    )
    db.session.add(event)
    db.session.commit()

    return jsonify({"status": "ok"})


@tracking_bp.route("/t/<code>", methods=["GET"])
def track_click(code):
    assignment = AdAssignment.query.filter_by(code=code).first()
    if not assignment:
        return jsonify({"error": "not_found"}), 404

    campaign = Campaign.query.get(assignment.campaign_id)
    if campaign:
        campaign.budget_spent = (campaign.budget_spent or Decimal("0")) + campaign.buyer_cpc

    event = TrackingEvent(
        assignment_id=assignment.id,
        campaign_id=assignment.campaign_id,
        ad_id=assignment.ad_id,
        partner_id=assignment.partner_id,
        event_type="click",
        created_at=datetime.utcnow(),
    )
    db.session.add(event)
    db.session.commit()

    destination_url = assignment.ad.destination_url
    return redirect(destination_url, code=302)
