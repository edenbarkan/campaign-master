from flask import Flask
from prometheus_flask_exporter import PrometheusMetrics

from app.config import Config
from app.extensions import db, migrate, jwt
from app.routes.analytics import analytics_bp
from app.routes.auth import auth_bp
from app.routes.buyer_ads import buyer_ads_bp
from app.routes.buyer_campaigns import buyer_campaigns_bp
from app.routes.health import health_bp
from app.routes.partner_ads import partner_ads_bp
from app.routes.tracking import tracking_bp


def create_app(config_override=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_override:
        app.config.update(config_override)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    PrometheusMetrics(app)

    from app import models  # noqa: F401

    app.register_blueprint(auth_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(buyer_ads_bp)
    app.register_blueprint(buyer_campaigns_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(partner_ads_bp)
    app.register_blueprint(tracking_bp)

    return app
