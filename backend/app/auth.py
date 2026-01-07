from flask import Blueprint, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.errors import json_error
from app.models import User

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    email = data.get('email')
    password = data.get('password')
    is_advertiser = data.get('is_advertiser', False)
    is_publisher = data.get('is_publisher', False)
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    # Check if user already exists
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'User with this email already exists'}), 409
    
    # Create new user
    user = User(
        email=email,
        is_advertiser=is_advertiser,
        is_publisher=is_publisher
    )
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        'message': 'User registered successfully',
        'user': {
            'id': user.id,
            'email': user.email,
            'is_advertiser': user.is_advertiser,
            'is_publisher': user.is_publisher
        }
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login a user."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    user = User.query.filter_by(email=email).first()
    
    if not user or not user.check_password(password):
        return json_error(401, 'Invalid email or password')
    
    try:
        login_user(user)
    except Exception as exc:
        current_app.logger.exception('Failed to log in user %s', email, exc_info=exc)
        return json_error(500, 'Internal Server Error')
    
    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user.id,
            'email': user.email,
            'is_advertiser': user.is_advertiser,
            'is_publisher': user.is_publisher
        }
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logout the current user."""
    logout_user()
    return jsonify({'message': 'Logout successful'}), 200


@auth_bp.route('/me', methods=['GET'])
@login_required
def me():
    """Get current user information."""
    return jsonify({
        'user': {
            'id': current_user.id,
            'email': current_user.email,
            'is_advertiser': current_user.is_advertiser,
            'is_publisher': current_user.is_publisher,
            'created_at': current_user.created_at.isoformat()
        }
    }), 200
