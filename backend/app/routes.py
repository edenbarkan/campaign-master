from flask import Blueprint, jsonify
from flask_login import current_user, login_required
from sqlalchemy import func, text

from app import db
from app.errors import json_error
from app.models import AdRequest, Campaign, Click, Impression, LedgerEntry

health_bp = Blueprint('health', __name__)
reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')


@health_bp.route('/healthz')
def healthz():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'}), 200


@health_bp.route('/readyz')
def readyz():
    """Readiness check endpoint - verifies database connection."""
    try:
        db.session.execute(text('SELECT 1'))
        return jsonify({'status': 'ready'}), 200
    except Exception as e:
        return jsonify({'status': 'not ready', 'error': str(e)}), 503


@reports_bp.route('/advertiser', methods=['GET'])
@login_required
def advertiser_report():
    """Totals report for the current advertiser."""
    if not current_user.is_advertiser:
        return json_error(403, 'Forbidden')
    impression_count = (
        db.session.query(func.coalesce(func.count(Impression.id), 0))
        .join(AdRequest, Impression.ad_request_id == AdRequest.id)
        .filter(AdRequest.advertiser_id == current_user.id)
        .scalar()
    )
    click_count = (
        db.session.query(func.coalesce(func.count(Click.id), 0))
        .join(AdRequest, Click.ad_request_id == AdRequest.id)
        .filter(AdRequest.advertiser_id == current_user.id)
        .scalar()
    )
    spend_micro = (
        db.session.query(func.coalesce(func.sum(LedgerEntry.amount_micro), 0))
        .filter(
            LedgerEntry.user_id == current_user.id,
            LedgerEntry.entry_type == 'spend',
            LedgerEntry.ref_type.in_(('impression', 'click')),
        )
        .scalar()
    )
    impression_count = int(impression_count or 0)
    click_count = int(click_count or 0)
    spend_micro = int(spend_micro or 0)

    return jsonify({
        'totals': {
            'impressions': impression_count or 0,
            'clicks': click_count or 0,
            'spend_micro': spend_micro or 0,
        }
    }), 200


@reports_bp.route('/publisher', methods=['GET'])
@login_required
def publisher_report():
    """Totals report for the current publisher."""
    if not current_user.is_publisher:
        return json_error(403, 'Forbidden')
    impression_count = (
        db.session.query(func.coalesce(func.count(Impression.id), 0))
        .join(AdRequest, Impression.ad_request_id == AdRequest.id)
        .filter(AdRequest.publisher_id == current_user.id)
        .scalar()
    )
    click_count = (
        db.session.query(func.coalesce(func.count(Click.id), 0))
        .join(AdRequest, Click.ad_request_id == AdRequest.id)
        .filter(AdRequest.publisher_id == current_user.id)
        .scalar()
    )
    earn_micro = (
        db.session.query(func.coalesce(func.sum(LedgerEntry.amount_micro), 0))
        .filter(
            LedgerEntry.user_id == current_user.id,
            LedgerEntry.entry_type == 'earn',
            LedgerEntry.ref_type.in_(('impression', 'click')),
        )
        .scalar()
    )
    impression_count = int(impression_count or 0)
    click_count = int(click_count or 0)
    earn_micro = int(earn_micro or 0)

    return jsonify({
        'totals': {
            'impressions': impression_count or 0,
            'clicks': click_count or 0,
            'earn_micro': earn_micro or 0,
        }
    }), 200
