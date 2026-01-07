import pytest
from app import create_app, db


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = False

    @app.route('/force-error')
    def force_error():
        raise RuntimeError('boom')

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_not_found_returns_json(client):
    response = client.get('/api/does-not-exist')
    assert response.status_code == 404
    assert response.get_json() == {'error': 'Not Found'}


def test_method_not_allowed_returns_json(client):
    response = client.post('/healthz')
    assert response.status_code == 405
    assert response.get_json() == {'error': 'Method Not Allowed'}


def test_internal_error_returns_json(client):
    response = client.get('/force-error')
    assert response.status_code == 500
    assert response.get_json() == {'error': 'Internal Server Error'}
