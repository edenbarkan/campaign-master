import os
import pytest
from app import create_app, db
from app.models import User, Wallet, LedgerEntry
from app.wallet_helpers import topup_balance, get_or_create_wallet


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


@pytest.fixture
def user_id(app):
    """Create a test user."""
    with app.app_context():
        user = User(
            email='test@example.com',
            is_advertiser=True,
            is_publisher=False
        )
        user.set_password('testpassword123')
        db.session.add(user)
        db.session.commit()
        return user.id


def test_get_wallet(client, user_id):
    """Test getting wallet information."""
    # Login first
    login_response = client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'testpassword123'
    })
    assert login_response.status_code == 200
    
    # Get wallet (should create if doesn't exist)
    wallet_response = client.get('/api/wallet')
    assert wallet_response.status_code == 200
    
    wallet_data = wallet_response.get_json()
    assert 'wallet' in wallet_data
    assert wallet_data['wallet']['user_id'] == user_id
    assert wallet_data['wallet']['balance_micro'] == 0
    assert wallet_data['wallet']['reserved_micro'] == 0
    assert wallet_data['wallet']['available_micro'] == 0


def test_topup_and_available_balance(client, user_id):
    """Test topup and verify available balance calculation."""
    # Login first
    login_response = client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'testpassword123'
    })
    assert login_response.status_code == 200
    
    # Topup with default amount (1,000,000 micro = 1.00)
    topup_response = client.post('/api/wallet/topup', json={})
    assert topup_response.status_code == 200
    
    topup_data = topup_response.get_json()
    assert topup_data['message'] == 'Topup successful'
    assert topup_data['wallet']['balance_micro'] == 1000000
    assert topup_data['wallet']['reserved_micro'] == 0
    assert topup_data['wallet']['available_micro'] == 1000000
    
    # Topup with custom amount (2,500,000 micro = 2.50)
    topup_response2 = client.post('/api/wallet/topup', json={
        'amount_micro': 2500000
    })
    assert topup_response2.status_code == 200
    
    topup_data2 = topup_response2.get_json()
    assert topup_data2['wallet']['balance_micro'] == 3500000  # 1.00 + 2.50
    assert topup_data2['wallet']['available_micro'] == 3500000
    
    # Get wallet to verify final state
    wallet_response = client.get('/api/wallet')
    assert wallet_response.status_code == 200
    
    wallet_data = wallet_response.get_json()
    assert wallet_data['wallet']['balance_micro'] == 3500000
    assert wallet_data['wallet']['available_micro'] == 3500000


def test_topup_with_ledger_entry(client, user_id, app):
    """Test that topup creates ledger entry."""
    # Login first
    login_response = client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'testpassword123'
    })
    assert login_response.status_code == 200
    
    # Topup
    topup_response = client.post('/api/wallet/topup', json={
        'amount_micro': 5000000
    })
    assert topup_response.status_code == 200
    
    # Verify ledger entry was created
    with app.app_context():
        ledger_entries = LedgerEntry.query.filter_by(
            user_id=user_id,
            entry_type='topup'
        ).all()
        assert len(ledger_entries) == 1
        assert ledger_entries[0].amount_micro == 5000000
        assert ledger_entries[0].ref_type == 'topup'


def test_topup_negative_amount(client, user_id):
    """Test that negative amounts are rejected."""
    # Login first
    login_response = client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'testpassword123'
    })
    assert login_response.status_code == 200
    
    # Try to topup with negative amount
    topup_response = client.post('/api/wallet/topup', json={
        'amount_micro': -1000
    })
    assert topup_response.status_code == 400


def test_topup_float_rejected(client, user_id):
    """Test that float amounts are rejected (must be integer)."""
    # Login first
    login_response = client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'testpassword123'
    })
    assert login_response.status_code == 200
    
    # Try to topup with float (should be rejected)
    topup_response = client.post('/api/wallet/topup', json={
        'amount_micro': 1000.5
    })
    assert topup_response.status_code == 400


def test_wallet_requires_authentication(client):
    """Test that wallet endpoints require authentication."""
    # Try to get wallet without login
    wallet_response = client.get('/api/wallet')
    assert wallet_response.status_code == 401
    wallet_error = wallet_response.get_json()['error']
    assert wallet_error == 'Unauthorized'
    
    # Try to topup without login
    topup_response = client.post('/api/wallet/topup', json={})
    assert topup_response.status_code == 401
    topup_error = topup_response.get_json()['error']
    assert topup_error == 'Unauthorized'


def test_wallet_topup_forbidden_for_publisher(client, app):
    """Publishers should not be allowed to top up wallets."""
    with app.app_context():
        publisher = User(
            email='publisher@example.com',
            is_advertiser=False,
            is_publisher=True
        )
        publisher.set_password('testpassword123')
        db.session.add(publisher)
        db.session.commit()
        publisher_id = publisher.id

    login_response = client.post('/api/auth/login', json={
        'email': 'publisher@example.com',
        'password': 'testpassword123'
    })
    assert login_response.status_code == 200

    topup_response = client.post('/api/wallet/topup', json={'amount_micro': 1000})
    assert topup_response.status_code == 403
    assert topup_response.get_json()['error'] == 'Forbidden'

    with app.app_context():
        wallet = Wallet.query.filter_by(user_id=publisher_id).first()
        assert wallet is None
