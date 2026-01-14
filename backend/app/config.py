import os
from decimal import Decimal, InvalidOperation


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@db:5432/campaign_master",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PLATFORM_FEE_PERCENT = os.getenv("PLATFORM_FEE_PERCENT", "30")


def load_platform_fee_percent(value):
    try:
        percent = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        percent = Decimal("30")
    if percent < 0:
        percent = Decimal("0")
    if percent > 100:
        percent = Decimal("100")
    return percent
