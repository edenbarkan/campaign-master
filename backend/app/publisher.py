from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.errors import json_error
from app.models import Site, Slot


publisher_bp = Blueprint('publisher', __name__, url_prefix='/api/publisher')


def check_site_ownership(site_id):
    """Check if current user owns the site."""
    site = Site.query.get_or_404(site_id)
    if site.user_id != current_user.id:
        return None, json_error(403, 'Forbidden')
    return site, None


# Site endpoints

@publisher_bp.route('/sites', methods=['POST'])
@login_required
def create_site():
    """Create a new site."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    name = data.get('name')
    domain = data.get('domain')
    
    if not name or not domain:
        return jsonify({'error': 'Name and domain are required'}), 400
    
    site = Site(
        user_id=current_user.id,
        name=name,
        domain=domain
    )
    
    db.session.add(site)
    db.session.commit()
    
    return jsonify({
        'message': 'Site created successfully',
        'site': {
            'id': site.id,
            'user_id': site.user_id,
            'name': site.name,
            'domain': site.domain,
            'created_at': site.created_at.isoformat()
        }
    }), 201


@publisher_bp.route('/sites', methods=['GET'])
@login_required
def list_sites():
    """List all sites for current user."""
    sites = Site.query.filter_by(user_id=current_user.id).all()
    
    return jsonify({
        'sites': [{
            'id': s.id,
            'user_id': s.user_id,
            'name': s.name,
            'domain': s.domain,
            'created_at': s.created_at.isoformat()
        } for s in sites]
    }), 200


@publisher_bp.route('/sites/<int:site_id>', methods=['PATCH'])
@login_required
def update_site(site_id):
    """Update site information."""
    site, error_response = check_site_ownership(site_id)
    if error_response:
        return error_response
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    if 'name' in data:
        site.name = data['name']
    if 'domain' in data:
        site.domain = data['domain']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Site updated successfully',
        'site': {
            'id': site.id,
            'name': site.name,
            'domain': site.domain
        }
    }), 200


# Slot endpoints

@publisher_bp.route('/sites/<int:site_id>/slots', methods=['POST'])
@login_required
def create_slot(site_id):
    """Create a new ad slot for a site."""
    site, error_response = check_site_ownership(site_id)
    if error_response:
        return error_response
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    name = data.get('name')
    width = data.get('width')
    height = data.get('height')
    
    if not name or not width or not height:
        return jsonify({'error': 'Name, width, and height are required'}), 400
    
    if width <= 0 or height <= 0:
        return jsonify({'error': 'Width and height must be positive'}), 400
    
    slot = Slot(
        site_id=site_id,
        name=name,
        width=width,
        height=height,
        floor_cpm_micro=data.get('floor_cpm_micro'),
        floor_cpc_micro=data.get('floor_cpc_micro'),
        status=data.get('status', 'active')
    )
    
    db.session.add(slot)
    db.session.commit()
    
    return jsonify({
        'message': 'Slot created successfully',
        'slot': {
            'id': slot.id,
            'site_id': slot.site_id,
            'name': slot.name,
            'width': slot.width,
            'height': slot.height,
            'floor_cpm_micro': slot.floor_cpm_micro,
            'floor_cpc_micro': slot.floor_cpc_micro,
            'status': slot.status,
            'created_at': slot.created_at.isoformat()
        }
    }), 201


@publisher_bp.route('/sites/<int:site_id>/slots', methods=['GET'])
@login_required
def list_slots(site_id):
    """List all slots for a site."""
    site, error_response = check_site_ownership(site_id)
    if error_response:
        return error_response
    
    slots = Slot.query.filter_by(site_id=site_id).all()
    
    return jsonify({
        'slots': [{
            'id': slot.id,
            'site_id': slot.site_id,
            'name': slot.name,
            'width': slot.width,
            'height': slot.height,
            'floor_cpm_micro': slot.floor_cpm_micro,
            'floor_cpc_micro': slot.floor_cpc_micro,
            'status': slot.status,
            'created_at': slot.created_at.isoformat()
        } for slot in slots]
    }), 200


@publisher_bp.route('/slots/<int:slot_id>/status', methods=['PATCH'])
@login_required
def update_slot_status(slot_id):
    """Update slot status."""
    slot = Slot.query.get_or_404(slot_id)
    site = Site.query.get_or_404(slot.site_id)
    
    if site.user_id != current_user.id:
        return json_error(403, 'Forbidden')
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    new_status = data.get('status')
    if not new_status:
        return jsonify({'error': 'Status is required'}), 400
    
    valid_statuses = ['active', 'paused', 'archived']
    if new_status not in valid_statuses:
        return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400
    
    slot.status = new_status
    db.session.commit()
    
    return jsonify({
        'message': 'Slot status updated successfully',
        'slot': {
            'id': slot.id,
            'status': slot.status
        }
    }), 200
