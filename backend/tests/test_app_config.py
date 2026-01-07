import os
from pathlib import Path

from sqlalchemy.engine.url import make_url

from app import create_app


def test_relative_sqlite_database_url_resolved(monkeypatch):
    backend_dir = Path(__file__).resolve().parent.parent
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///custom_relative.db')

    original_cwd = os.getcwd()
    os.chdir('/')
    try:
        app = create_app()
    finally:
        os.chdir(original_cwd)

    resolved_url = make_url(app.config['SQLALCHEMY_DATABASE_URI'])
    expected_path = backend_dir / 'instance' / 'custom_relative.db'
    assert Path(resolved_url.database) == expected_path
