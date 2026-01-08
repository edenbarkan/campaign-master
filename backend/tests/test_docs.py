import os
import pytest
from app import create_app, db


@pytest.fixture
def app():
    db_url = os.getenv('DATABASE_URL', 'sqlite:///:memory:')
    if not db_url:
        db_url = 'sqlite:///:memory:'
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': db_url,
        'SECRET_KEY': 'test-secret',
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_openapi_yaml_served(client):
    response = client.get('/openapi.yaml')
    assert response.status_code == 200
    assert b'openapi:' in response.data


def test_docs_swagger_ui(client):
    response = client.get('/docs')
    assert response.status_code == 200
    assert b'SwaggerUIBundle' in response.data
