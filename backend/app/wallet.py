from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.errors import json_error
from app.models import Wallet
from app.wallet_helpers import get_or_create_wallet, topup_balance

wallet_bp = Blueprint('wallet', __name__, url_prefix='/api/wallet')


@wallet_bp.route('', methods=['GET'])
@login_required
def get_wallet():
    """Get current user's wallet information."""
    wallet = get_or_create_wallet(current_user.id)
    
    available_micro = wallet.balance_micro - wallet.reserved_micro
    
    return jsonify({
        'wallet': {
            'user_id': wallet.user_id,
            'balance_micro': wallet.balance_micro,
            'reserved_micro': wallet.reserved_micro,
            'available_micro': available_micro,
            'created_at': wallet.created_at.isoformat()
        }
    }), 200


@wallet_bp.route('/topup', methods=['POST'])
@login_required
def topup():
    """Top up wallet balance (demo amount)."""
    if not current_user.is_advertiser:
        return json_error(403, 'Forbidden')
    data = request.get_json() or {}
    
    # For demo, use a fixed amount or allow amount_micro in request
    if 'amount_micro' in data and data['amount_micro'] is not None:
        amount_micro = data['amount_micro']
    elif 'amount' in data and data['amount'] is not None:
        amount_micro = data['amount']
    else:
        amount_micro = 1000000  # Default: 1.00 (1,000,000 micro)
    
    if amount_micro <= 0:
        return jsonify({'error': 'Amount must be positive'}), 400
    
    if not isinstance(amount_micro, int):
        return jsonify({'error': 'Amount must be an integer (micro units)'}), 400
    
    success, wallet = topup_balance(
        current_user.id,
        amount_micro,
        ref_type='topup',
        ref_id=None
    )
    
    if not success:
        return jsonify({'error': 'Failed to process topup'}), 500
    
    available_micro = wallet.balance_micro - wallet.reserved_micro
    
    return jsonify({
        'message': 'Topup successful',
        'wallet': {
            'user_id': wallet.user_id,
            'balance_micro': wallet.balance_micro,
            'reserved_micro': wallet.reserved_micro,
            'available_micro': available_micro
        }
    }), 200
