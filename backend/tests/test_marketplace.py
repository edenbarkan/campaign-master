import os
import pytest
from app import create_app, db
from app.models import User, Campaign, Ad, Site, Slot


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
def advertiser_user(app):
    """Create an advertiser user."""
    with app.app_context():
        user = User(
            email='advertiser@example.com',
            is_advertiser=True,
            is_publisher=False
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def publisher_user(app):
    """Create a publisher user."""
    with app.app_context():
        user = User(
            email='publisher@example.com',
            is_advertiser=False,
            is_publisher=True
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def other_user(app):
    """Create another user."""
    with app.app_context():
        user = User(
            email='other@example.com',
            is_advertiser=True,
            is_publisher=False
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return user


def login_user(client, email, password):
    """Helper to login a user."""
    return client.post('/api/auth/login', json={
        'email': email,
        'password': password
    })


def test_campaign_ownership_enforcement(client, advertiser_user, other_user, app):
    """Test that only campaign owner can manage their campaigns."""
    # Login as advertiser
    login_user(client, 'advertiser@example.com', 'password123')
    
    # Create a campaign
    create_response = client.post('/api/advertiser/campaigns', json={
        'name': 'Test Campaign',
        'status': 'draft',
        'bid_cpm_micro': 1000000
    })
    assert create_response.status_code == 201
    campaign_data = create_response.get_json()
    campaign_id = campaign_data['campaign']['id']
    
    # Update status as owner (should succeed)
    update_response = client.patch(f'/api/advertiser/campaigns/{campaign_id}/status', json={
        'status': 'active'
    })
    assert update_response.status_code == 200
    
    # Logout
    client.post('/api/auth/logout')
    
    # Login as other user
    login_user(client, 'other@example.com', 'password123')
    
    # Try to update status as non-owner (should fail)
    update_response = client.patch(f'/api/advertiser/campaigns/{campaign_id}/status', json={
        'status': 'paused'
    })
    assert update_response.status_code == 403
    error_message = update_response.get_json()['error']
    assert error_message == 'Forbidden'


def test_ad_ownership_enforcement(client, advertiser_user, other_user, app):
    """Test that only campaign owner can manage ads."""
    # Login as advertiser
    login_user(client, 'advertiser@example.com', 'password123')
    
    # Create a campaign
    create_campaign = client.post('/api/advertiser/campaigns', json={
        'name': 'Test Campaign',
        'status': 'active'
    })
    campaign_id = create_campaign.get_json()['campaign']['id']
    
    # Create an ad
    create_ad = client.post(f'/api/advertiser/campaigns/{campaign_id}/ads', json={
        'title': 'Test Ad',
        'image_url': 'https://example.com/image.jpg',
        'landing_url': 'https://example.com',
        'status': 'active'
    })
    assert create_ad.status_code == 201
    ad_id = create_ad.get_json()['ad']['id']
    
    # Update ad status as owner (should succeed)
    update_response = client.patch(f'/api/advertiser/ads/{ad_id}/status', json={
        'status': 'paused'
    })
    assert update_response.status_code == 200
    
    # Logout
    client.post('/api/auth/logout')
    
    # Login as other user
    login_user(client, 'other@example.com', 'password123')
    
    # Try to update ad status as non-owner (should fail)
    update_response = client.patch(f'/api/advertiser/ads/{ad_id}/status', json={
        'status': 'active'
    })
    assert update_response.status_code == 403
    error_message = update_response.get_json()['error']
    assert error_message == 'Forbidden'


def test_site_ownership_enforcement(client, publisher_user, other_user, app):
    """Test that only site owner can manage their sites."""
    # Login as publisher
    login_user(client, 'publisher@example.com', 'password123')
    
    # Create a site
    create_response = client.post('/api/publisher/sites', json={
        'name': 'Test Site',
        'domain': 'example.com'
    })
    assert create_response.status_code == 201
    site_id = create_response.get_json()['site']['id']
    
    # Update site as owner (should succeed)
    update_response = client.patch(f'/api/publisher/sites/{site_id}', json={
        'name': 'Updated Site Name'
    })
    assert update_response.status_code == 200
    
    # Logout
    client.post('/api/auth/logout')
    
    # Login as other user
    login_user(client, 'other@example.com', 'password123')
    
    # Try to update site as non-owner (should fail)
    update_response = client.patch(f'/api/publisher/sites/{site_id}', json={
        'name': 'Hacked Site'
    })
    assert update_response.status_code == 403
    error_message = update_response.get_json()['error']
    assert error_message == 'Forbidden'


def test_slot_ownership_enforcement(client, publisher_user, other_user, app):
    """Test that only site owner can manage slots."""
    # Login as publisher
    login_user(client, 'publisher@example.com', 'password123')
    
    # Create a site
    create_site = client.post('/api/publisher/sites', json={
        'name': 'Test Site',
        'domain': 'example.com'
    })
    site_id = create_site.get_json()['site']['id']
    
    # Create a slot
    create_slot = client.post(f'/api/publisher/sites/{site_id}/slots', json={
        'name': 'Test Slot',
        'width': 300,
        'height': 250,
        'floor_cpm_micro': 500000,
        'status': 'active'
    })
    assert create_slot.status_code == 201
    slot_id = create_slot.get_json()['slot']['id']
    
    # Update slot status as owner (should succeed)
    update_response = client.patch(f'/api/publisher/slots/{slot_id}/status', json={
        'status': 'paused'
    })
    assert update_response.status_code == 200
    
    # Logout
    client.post('/api/auth/logout')
    
    # Login as other user
    login_user(client, 'other@example.com', 'password123')
    
    # Try to update slot status as non-owner (should fail)
    update_response = client.patch(f'/api/publisher/slots/{slot_id}/status', json={
        'status': 'active'
    })
    assert update_response.status_code == 403
    error_message = update_response.get_json()['error']
    assert error_message == 'Forbidden'


def test_campaign_list_only_owner_campaigns(client, advertiser_user, other_user, app):
    """Test that users only see their own campaigns."""
    # Login as advertiser
    login_user(client, 'advertiser@example.com', 'password123')
    
    # Create a campaign
    client.post('/api/advertiser/campaigns', json={
        'name': 'Advertiser Campaign',
        'status': 'active'
    })
    
    # Logout
    client.post('/api/auth/logout')
    
    # Login as other user
    login_user(client, 'other@example.com', 'password123')
    
    # Create another campaign
    client.post('/api/advertiser/campaigns', json={
        'name': 'Other Campaign',
        'status': 'active'
    })
    
    # List campaigns - should only see own campaign
    list_response = client.get('/api/advertiser/campaigns')
    assert list_response.status_code == 200
    campaigns = list_response.get_json()['campaigns']
    assert len(campaigns) == 1
    assert campaigns[0]['name'] == 'Other Campaign'


def test_site_list_only_owner_sites(client, publisher_user, other_user, app):
    """Test that users only see their own sites."""
    # Login as publisher
    login_user(client, 'publisher@example.com', 'password123')
    
    # Create a site
    client.post('/api/publisher/sites', json={
        'name': 'Publisher Site',
        'domain': 'publisher.com'
    })
    
    # Logout
    client.post('/api/auth/logout')
    
    # Login as other user
    login_user(client, 'other@example.com', 'password123')
    
    # Create another site
    client.post('/api/publisher/sites', json={
        'name': 'Other Site',
        'domain': 'other.com'
    })
    
    # List sites - should only see own site
    list_response = client.get('/api/publisher/sites')
    assert list_response.status_code == 200
    sites = list_response.get_json()['sites']
    assert len(sites) == 1
    assert sites[0]['name'] == 'Other Site'
