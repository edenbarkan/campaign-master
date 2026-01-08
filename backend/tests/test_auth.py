import os
import pytest
from app import create_app, db
from app.models import User


@pytest.fixture
def app():
    """Create application for testing."""
    db_url = os.getenv('DATABASE_URL', 'sqlite:///:memory:')
    if not db_url:
        db_url = 'sqlite:///:memory:'
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': db_url,
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def test_register_and_login_flow(client):
    """Test user registration and login flow."""
    # Register a new user
    register_response = client.post('/api/auth/register', json={
        'email': 'test@example.com',
        'password': 'testpassword123',
        'is_advertiser': True,
        'is_publisher': False
    })
    
    assert register_response.status_code == 201
    register_data = register_response.get_json()
    assert register_data['message'] == 'User registered successfully'
    assert register_data['user']['email'] == 'test@example.com'
    assert register_data['user']['is_advertiser'] is True
    assert register_data['user']['is_publisher'] is False
    
    # Login with the registered user
    login_response = client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'testpassword123'
    })
    
    assert login_response.status_code == 200
    login_data = login_response.get_json()
    assert login_data['message'] == 'Login successful'
    assert login_data['user']['email'] == 'test@example.com'
    
    # Get current user info
    me_response = client.get('/api/auth/me')
    assert me_response.status_code == 200
    me_data = me_response.get_json()
    assert me_data['user']['email'] == 'test@example.com'
    
    # Logout
    logout_response = client.post('/api/auth/logout')
    assert logout_response.status_code == 200
    
    # Try to access /me after logout (should fail)
    me_after_logout = client.get('/api/auth/me')
    assert me_after_logout.status_code == 401
    me_error = me_after_logout.get_json()['error']
    assert me_error == 'Unauthorized'


def test_login_handles_missing_password_hash(client, app):
    """Legacy users without password hash should not trigger 500."""
    with app.app_context():
        legacy_user = User(
            email='legacy@example.com',
            is_advertiser=True,
            is_publisher=False
        )
        legacy_user.password_hash = ''
        db.session.add(legacy_user)
        db.session.commit()

    response = client.post('/api/auth/login', json={
        'email': 'legacy@example.com',
        'password': 'whatever'
    })
    assert response.status_code == 401
    data = response.get_json()
    assert data['error'] == 'Invalid email or password'


def test_login_invalid_user_never_500(client):
    """Logging in with an unknown user should return 401, not 500."""
    response = client.post('/api/auth/login', json={
        'email': 'unknown@example.com',
        'password': 'password123'
    })
    assert response.status_code == 401
    assert response.get_json()['error'] == 'Invalid email or password'


def test_successful_login_sets_session_cookie(client):
    """Successful login should set a session cookie for Flask-Login."""
    register_response = client.post('/api/auth/register', json={
        'email': 'cookie@example.com',
        'password': 'cookiepass123',
        'is_advertiser': True,
        'is_publisher': False
    })
    assert register_response.status_code == 201

    login_response = client.post('/api/auth/login', json={
        'email': 'cookie@example.com',
        'password': 'cookiepass123'
    })
    assert login_response.status_code == 200
    cookies = login_response.headers.getlist('Set-Cookie')
    assert any(cookie.startswith('session=') for cookie in cookies)
