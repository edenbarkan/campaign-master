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
    CLICK_HASH_SALT = os.getenv("CLICK_HASH_SALT", "devsalt")
    CLICK_DUPLICATE_WINDOW_SECONDS = int(os.getenv("CLICK_DUPLICATE_WINDOW_SECONDS", "10"))
    CLICK_RATE_LIMIT_PER_MINUTE = int(os.getenv("CLICK_RATE_LIMIT_PER_MINUTE", "20"))
    IMPRESSION_DEDUP_WINDOW_SECONDS = int(
        os.getenv("IMPRESSION_DEDUP_WINDOW_SECONDS", "60")
    )
    FREQ_CAP_SECONDS = int(os.getenv("FREQ_CAP_SECONDS", "60"))
    MATCH_CTR_LOOKBACK_DAYS = int(os.getenv("MATCH_CTR_LOOKBACK_DAYS", "14"))
    MATCH_REJECT_LOOKBACK_DAYS = int(os.getenv("MATCH_REJECT_LOOKBACK_DAYS", "7"))
    MATCH_CTR_WEIGHT = float(os.getenv("MATCH_CTR_WEIGHT", "1.0"))
    MATCH_TARGETING_BONUS = float(os.getenv("MATCH_TARGETING_BONUS", "0.5"))
    MATCH_REJECT_PENALTY_WEIGHT = float(os.getenv("MATCH_REJECT_PENALTY_WEIGHT", "1.0"))
    MATCHING_DEBUG = os.getenv("MATCHING_DEBUG", "0")


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
