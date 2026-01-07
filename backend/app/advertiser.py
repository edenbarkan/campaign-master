from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.errors import json_error
from app.models import Campaign, Ad


advertiser_bp = Blueprint('advertiser', __name__, url_prefix='/api/advertiser')


def check_campaign_ownership(campaign_id):
    """Check if current user owns the campaign."""
    campaign = Campaign.query.get_or_404(campaign_id)
    if campaign.user_id != current_user.id:
        return None, json_error(403, 'Forbidden')
    return campaign, None


# Campaign endpoints

@advertiser_bp.route('/campaigns', methods=['POST'])
@login_required
def create_campaign():
    """Create a new campaign."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    name = data.get('name')
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    
    campaign = Campaign(
        user_id=current_user.id,
        name=name,
        status=data.get('status', 'draft'),
        bid_cpm_micro=data.get('bid_cpm_micro'),
        bid_cpc_micro=data.get('bid_cpc_micro')
    )
    
    db.session.add(campaign)
    db.session.commit()
    
    return jsonify({
        'message': 'Campaign created successfully',
        'campaign': {
            'id': campaign.id,
            'user_id': campaign.user_id,
            'name': campaign.name,
            'status': campaign.status,
            'bid_cpm_micro': campaign.bid_cpm_micro,
            'bid_cpc_micro': campaign.bid_cpc_micro,
            'created_at': campaign.created_at.isoformat()
        }
    }), 201


@advertiser_bp.route('/campaigns', methods=['GET'])
@login_required
def list_campaigns():
    """List all campaigns for current user."""
    campaigns = Campaign.query.filter_by(user_id=current_user.id).all()
    
    return jsonify({
        'campaigns': [{
            'id': c.id,
            'user_id': c.user_id,
            'name': c.name,
            'status': c.status,
            'bid_cpm_micro': c.bid_cpm_micro,
            'bid_cpc_micro': c.bid_cpc_micro,
            'created_at': c.created_at.isoformat()
        } for c in campaigns]
    }), 200


@advertiser_bp.route('/campaigns/<int:campaign_id>/status', methods=['PATCH'])
@login_required
def update_campaign_status(campaign_id):
    """Update campaign status."""
    campaign, error_response = check_campaign_ownership(campaign_id)
    if error_response:
        return error_response
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    new_status = data.get('status')
    if not new_status:
        return jsonify({'error': 'Status is required'}), 400
    
    valid_statuses = ['draft', 'active', 'paused', 'archived']
    if new_status not in valid_statuses:
        return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400
    
    campaign.status = new_status
    db.session.commit()
    
    return jsonify({
        'message': 'Campaign status updated successfully',
        'campaign': {
            'id': campaign.id,
            'status': campaign.status
        }
    }), 200


# Ad endpoints

@advertiser_bp.route('/campaigns/<int:campaign_id>/ads', methods=['POST'])
@login_required
def create_ad(campaign_id):
    """Create a new ad for a campaign."""
    campaign, error_response = check_campaign_ownership(campaign_id)
    if error_response:
        return error_response
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    title = data.get('title')
    image_url = data.get('image_url')
    landing_url = data.get('landing_url')
    
    if not title or not image_url or not landing_url:
        return jsonify({'error': 'Title, image_url, and landing_url are required'}), 400
    
    ad = Ad(
        campaign_id=campaign_id,
        title=title,
        image_url=image_url,
        landing_url=landing_url,
        status=data.get('status', 'draft')
    )
    
    db.session.add(ad)
    db.session.commit()
    
    return jsonify({
        'message': 'Ad created successfully',
        'ad': {
            'id': ad.id,
            'campaign_id': ad.campaign_id,
            'title': ad.title,
            'image_url': ad.image_url,
            'landing_url': ad.landing_url,
            'status': ad.status,
            'created_at': ad.created_at.isoformat()
        }
    }), 201


@advertiser_bp.route('/campaigns/<int:campaign_id>/ads', methods=['GET'])
@login_required
def list_ads(campaign_id):
    """List all ads for a campaign."""
    campaign, error_response = check_campaign_ownership(campaign_id)
    if error_response:
        return error_response
    
    ads = Ad.query.filter_by(campaign_id=campaign_id).all()
    
    return jsonify({
        'ads': [{
            'id': ad.id,
            'campaign_id': ad.campaign_id,
            'title': ad.title,
            'image_url': ad.image_url,
            'landing_url': ad.landing_url,
            'status': ad.status,
            'created_at': ad.created_at.isoformat()
        } for ad in ads]
    }), 200


@advertiser_bp.route('/ads/<int:ad_id>/status', methods=['PATCH'])
@login_required
def update_ad_status(ad_id):
    """Update ad status."""
    ad = Ad.query.get_or_404(ad_id)
    campaign = Campaign.query.get_or_404(ad.campaign_id)
    
    if campaign.user_id != current_user.id:
        return json_error(403, 'Forbidden')
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    new_status = data.get('status')
    if not new_status:
        return jsonify({'error': 'Status is required'}), 400
    
    valid_statuses = ['draft', 'active', 'paused', 'archived']
    if new_status not in valid_statuses:
        return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400
    
    ad.status = new_status
    db.session.commit()
    
    return jsonify({
        'message': 'Ad status updated successfully',
        'ad': {
            'id': ad.id,
            'status': ad.status
        }
    }), 200
