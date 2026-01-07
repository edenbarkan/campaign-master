import uuid
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, make_response, request
from sqlalchemy.orm import joinedload

from app import db
from app.adserver.service import release_expired_reservations
from app.models import Ad, AdRequest, Campaign, Slot, Wallet, LedgerEntry, Impression, Click

adserver_bp = Blueprint('adserver', __name__, url_prefix='/api')


class ReservationError(Exception):
    """Raised when an ad cannot be reserved due to insufficient balance."""


def _eligible_ads_for_slot(slot):
    floor_cpm = slot.floor_cpm_micro or 0
    floor_cpc = slot.floor_cpc_micro or 0

    return (
        Ad.query.options(joinedload(Ad.campaign))
        .join(Campaign, Ad.campaign_id == Campaign.id)
        .filter(
            Ad.status == 'active',
            Campaign.status == 'active',
            Campaign.bid_cpm_micro.isnot(None),
            Campaign.bid_cpc_micro.isnot(None),
            Campaign.bid_cpm_micro >= floor_cpm,
            Campaign.bid_cpc_micro >= floor_cpc,
        )
        .order_by(Campaign.created_at.asc())
    )


@adserver_bp.route('/adserve', methods=['GET'])
def adserve():
    slot_id = request.args.get('slot_id', type=int)
    if not slot_id:
        return jsonify({'error': 'slot_id is required'}), 400

    slot = Slot.query.options(joinedload(Slot.site)).get(slot_id)
    if not slot or slot.status != 'active' or not slot.site:
        return jsonify({'error': 'Slot not found'}), 404

    candidates = _eligible_ads_for_slot(slot).all()
    if not candidates:
        return ('', 204)

    price_cpm_micro = slot.floor_cpm_micro or 0
    price_cpc_micro = slot.floor_cpc_micro or 0
    impression_cost_micro = max(1, price_cpm_micro // 1000)
    click_cost_micro = price_cpc_micro
    required_micro = impression_cost_micro + click_cost_micro

    now = datetime.now(timezone.utc)
    reserved_until = now + timedelta(minutes=5)

    session = db.session()

    for ad in candidates:
        campaign = ad.campaign

        try:
            begin_transaction = (
                session.begin_nested if session.in_transaction() else session.begin
            )

            with begin_transaction():
                release_expired_reservations(session, now=now)

                wallet = (
                    session.query(Wallet)
                    .filter(Wallet.user_id == campaign.user_id)
                    .with_for_update()
                    .one_or_none()
                )

                if not wallet:
                    raise ReservationError('Wallet missing')

                available_micro = wallet.balance_micro - wallet.reserved_micro
                if available_micro < required_micro:
                    raise ReservationError('Insufficient balance')

                wallet.reserved_micro += required_micro

                request_id = str(uuid.uuid4())
                ad_request = AdRequest(
                    request_id=request_id,
                    advertiser_id=campaign.user_id,
                    publisher_id=slot.site.user_id,
                    campaign_id=campaign.id,
                    ad_id=ad.id,
                    slot_id=slot.id,
                    price_cpm_micro=price_cpm_micro,
                    price_cpc_micro=price_cpc_micro,
                    reserved_impression_micro=impression_cost_micro,
                    reserved_click_micro=click_cost_micro,
                    reserved_until=reserved_until,
                    impression_tracked_at=None,
                    click_tracked_at=None,
                    status='active',
                )

                session.add(ad_request)

            ad_html = (
                f'<div class="ad">'
                f'<a href="/api/track/click?request_id={request_id}" target="_blank">'
                f'<img src="{ad.image_url}" alt="{ad.title}"/>'
                f'</a>'
                f'<img src="/api/track/impression?request_id={request_id}" '
                f'style="display:none;" alt=""/>'
                f'</div>'
            )
            response = make_response(ad_html, 200)
            response.headers['Content-Type'] = 'text/html'
            return response

        except ReservationError:
            session.rollback()
            continue

    return ('', 204)


@adserver_bp.route('/track/impression', methods=['GET'])
def track_impression():
    request_id = request.args.get('request_id')
    if not request_id:
        return jsonify({'error': 'request_id is required'}), 400

    session = db.session()

    ad_request = session.query(AdRequest).filter_by(request_id=request_id).one_or_none()
    if not ad_request:
        return jsonify({'error': 'AdRequest not found'}), 404

    if ad_request.status != 'active':
        return ('', 410)

    if ad_request.impression_tracked_at is not None:
        return ('', 204)

    begin_transaction = session.begin_nested if session.in_transaction() else session.begin

    with begin_transaction():
        locked_request = (
            session.query(AdRequest)
            .filter(AdRequest.id == ad_request.id)
            .with_for_update()
            .one()
        )

        if locked_request.status != 'active':
            return ('', 410)

        if locked_request.impression_tracked_at is not None:
            return ('', 204)

        charge = locked_request.reserved_impression_micro

        advertiser_wallet = (
            session.query(Wallet)
            .filter(Wallet.user_id == locked_request.advertiser_id)
            .with_for_update()
            .one_or_none()
        )
        publisher_wallet = (
            session.query(Wallet)
            .filter(Wallet.user_id == locked_request.publisher_id)
            .with_for_update()
            .one_or_none()
        )

        insufficient_funds = (
            not advertiser_wallet
            or not publisher_wallet
            or advertiser_wallet.reserved_micro < charge
            or advertiser_wallet.balance_micro < charge
        )

        if insufficient_funds:
            locked_request.status = 'expired'
            return ('', 409)

        advertiser_wallet.reserved_micro -= charge
        advertiser_wallet.balance_micro -= charge
        publisher_wallet.balance_micro += charge

        spend_entry = LedgerEntry(
            user_id=locked_request.advertiser_id,
            entry_type='spend',
            amount_micro=charge,
            ref_type='impression',
            ref_id=locked_request.id,
        )
        earn_entry = LedgerEntry(
            user_id=locked_request.publisher_id,
            entry_type='earn',
            amount_micro=charge,
            ref_type='impression',
            ref_id=locked_request.id,
        )

        session.add_all([spend_entry, earn_entry])

        impression = Impression(
            ad_request_id=locked_request.id,
            price_micro=charge,
        )
        session.add(impression)

        locked_request.impression_tracked_at = datetime.utcnow()

    return ('', 204)


@adserver_bp.route('/track/click', methods=['GET'])
def track_click():
    request_id = request.args.get('request_id')
    if not request_id:
        return jsonify({'error': 'request_id is required'}), 400

    session = db.session()

    ad_request = session.query(AdRequest).filter_by(request_id=request_id).one_or_none()
    if not ad_request:
        return jsonify({'error': 'AdRequest not found'}), 404

    if ad_request.status != 'active':
        return ('', 410)

    ad = session.query(Ad).filter_by(id=ad_request.ad_id).one_or_none()
    if not ad:
        return jsonify({'error': 'Ad not found'}), 404

    landing_url = ad.landing_url

    if ad_request.click_tracked_at is not None:
        return make_response('', 302, {'Location': landing_url})

    begin_transaction = session.begin_nested if session.in_transaction() else session.begin

    with begin_transaction():
        locked_request = (
            session.query(AdRequest)
            .filter(AdRequest.id == ad_request.id)
            .with_for_update()
            .one()
        )

        if locked_request.status != 'active':
            return ('', 410)

        if locked_request.click_tracked_at is not None:
            return make_response('', 302, {'Location': landing_url})

        charge = locked_request.reserved_click_micro

        advertiser_wallet = (
            session.query(Wallet)
            .filter(Wallet.user_id == locked_request.advertiser_id)
            .with_for_update()
            .one_or_none()
        )
        publisher_wallet = (
            session.query(Wallet)
            .filter(Wallet.user_id == locked_request.publisher_id)
            .with_for_update()
            .one_or_none()
        )

        insufficient_funds = (
            not advertiser_wallet
            or not publisher_wallet
            or advertiser_wallet.reserved_micro < charge
            or advertiser_wallet.balance_micro < charge
        )

        if insufficient_funds:
            locked_request.status = 'expired'
            return ('', 409)

        advertiser_wallet.reserved_micro -= charge
        advertiser_wallet.balance_micro -= charge
        publisher_wallet.balance_micro += charge

        spend_entry = LedgerEntry(
            user_id=locked_request.advertiser_id,
            entry_type='spend',
            amount_micro=charge,
            ref_type='click',
            ref_id=locked_request.id,
        )
        earn_entry = LedgerEntry(
            user_id=locked_request.publisher_id,
            entry_type='earn',
            amount_micro=charge,
            ref_type='click',
            ref_id=locked_request.id,
        )

        session.add_all([spend_entry, earn_entry])

        click = Click(
            ad_request_id=locked_request.id,
            price_micro=charge,
        )
        session.add(click)

        locked_request.click_tracked_at = datetime.utcnow()

    response = make_response('', 302)
    response.headers['Location'] = landing_url
    return response
