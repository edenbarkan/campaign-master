import os
from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
from sqlalchemy.engine.url import make_url
from werkzeug.exceptions import HTTPException
from app.errors import json_error

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    from app.models import User
    return User.query.get(int(user_id))


def create_app(config_overrides=None):
    """Application factory pattern."""
    app = Flask(__name__)
    
    # Load environment variables
    load_dotenv()
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    instance_dir = os.path.join(base_dir, 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    default_db_path = os.path.join(instance_dir, 'campaign_master.db')
    default_db_uri = f"sqlite:///{default_db_path}"
    raw_database_url = os.getenv('DATABASE_URL')
    resolved_db_uri = _resolve_database_uri(raw_database_url, instance_dir, default_db_uri)
    app.config['SQLALCHEMY_DATABASE_URI'] = resolved_db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        secret_key = 'dev-secret-key-change-in-production'
        app.logger.warning('SECRET_KEY not provided; using development fallback. Do not use in production.')
    app.config['SECRET_KEY'] = secret_key

    if config_overrides:
        app.config.update(config_overrides)

    active_db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    app.logger.info('DATABASE_URL resolved to %s', active_db_uri)
    _log_database_path(app, active_db_uri)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = None
    
    # Customize unauthorized responses for API endpoints
    @login_manager.unauthorized_handler
    def unauthorized():
        return json_error(401, 'Unauthorized')

    # Register blueprints
    from app.routes import health_bp, reports_bp
    from app.auth import auth_bp
    from app.wallet import wallet_bp
    from app.advertiser import advertiser_bp
    from app.publisher import publisher_bp
    from app.adserver import adserver_bp
    from app.docs import docs_bp
    app.register_blueprint(health_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(wallet_bp)
    app.register_blueprint(advertiser_bp)
    app.register_blueprint(publisher_bp)
    app.register_blueprint(adserver_bp)
    app.register_blueprint(docs_bp)
    
    register_error_handlers(app)
    
    return app


def register_error_handlers(app):
    """Ensure all errors return JSON responses."""
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        status_code = error.code or 500
        description = getattr(error, 'description', None)
        message = description if (status_code == 400 and description) else None
        return json_error(status_code, message=message)

    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        app.logger.exception('Unhandled exception', exc_info=error)
        return json_error(500, 'Internal Server Error')


def _resolve_database_uri(raw_database_url, instance_dir, default_uri):
    """Ensure sqlite paths are absolute and anchored to the instance dir."""
    if not raw_database_url:
        return default_uri

    try:
        url = make_url(raw_database_url)
    except Exception:
        return raw_database_url

    if not url.drivername.startswith('sqlite'):
        return raw_database_url

    database = url.database
    if database in (None, '', ':memory:'):
        return raw_database_url

    if not os.path.isabs(database):
        database = os.path.abspath(os.path.join(instance_dir, database))
        url = url.set(database=database)
        return str(url)

    return raw_database_url


def _log_database_path(app, database_uri):
    """Log the resolved database path for easier debugging."""
    try:
        url = make_url(database_uri)
    except Exception:
        app.logger.info('Using database URI: %s', database_uri)
        return

    if url.drivername.startswith('sqlite') and url.database:
        app.logger.info('Using SQLite database at %s', url.database)
    else:
        app.logger.info('Using database URI: %s', database_uri)
