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
    MARKET_HEALTH_WINDOW_MINUTES = int(os.getenv("MARKET_HEALTH_WINDOW_MINUTES", "60"))
    MARKET_HEALTH_STREAK_SAMPLE = int(os.getenv("MARKET_HEALTH_STREAK_SAMPLE", "10"))
    MARKET_HEALTH_FILL_LOW = float(os.getenv("MARKET_HEALTH_FILL_LOW", "0.5"))
    MARKET_HEALTH_FILL_HIGH = float(os.getenv("MARKET_HEALTH_FILL_HIGH", "0.8"))
    MARKET_HEALTH_ELIGIBLE_SUPPLY_LOW = float(
        os.getenv("MARKET_HEALTH_ELIGIBLE_SUPPLY_LOW", "0.5")
    )
    MARKET_HEALTH_REJECT_VOLATILITY_THRESHOLD = float(
        os.getenv("MARKET_HEALTH_REJECT_VOLATILITY_THRESHOLD", "0.1")
    )
    MARKET_HEALTH_UNFILLED_STREAK_THRESHOLD = int(
        os.getenv("MARKET_HEALTH_UNFILLED_STREAK_THRESHOLD", "3")
    )
    MARKET_HEALTH_REJECT_HEALTHY = float(os.getenv("MARKET_HEALTH_REJECT_HEALTHY", "0.05"))
    ALPHA_PROFIT_BOOST_LOW_FILL = float(os.getenv("ALPHA_PROFIT_BOOST_LOW_FILL", "0.2"))
    ALPHA_PROFIT_BOOST_LOW_SUPPLY = float(os.getenv("ALPHA_PROFIT_BOOST_LOW_SUPPLY", "0.1"))
    BETA_CTR_BOOST_HEALTHY = float(os.getenv("BETA_CTR_BOOST_HEALTHY", "0.1"))
    GAMMA_TARGETING_BOOST_LOW_FILL = float(
        os.getenv("GAMMA_TARGETING_BOOST_LOW_FILL", "0.1")
    )
    GAMMA_TARGETING_BOOST_UNFILLED = float(
        os.getenv("GAMMA_TARGETING_BOOST_UNFILLED", "0.1")
    )
    DELTA_QUALITY_BOOST_LOW_FILL = float(
        os.getenv("DELTA_QUALITY_BOOST_LOW_FILL", "0.2")
    )
    DELTA_QUALITY_BOOST_VOLATILITY = float(
        os.getenv("DELTA_QUALITY_BOOST_VOLATILITY", "0.1")
    )
    PARTNER_QUALITY_NEW_CLICKS = int(os.getenv("PARTNER_QUALITY_NEW_CLICKS", "10"))
    PARTNER_QUALITY_RECENT_DAYS = int(os.getenv("PARTNER_QUALITY_RECENT_DAYS", "1"))
    PARTNER_QUALITY_LONG_DAYS = int(os.getenv("PARTNER_QUALITY_LONG_DAYS", "7"))
    PARTNER_QUALITY_RISKY_REJECT_RATE = float(
        os.getenv("PARTNER_QUALITY_RISKY_REJECT_RATE", "0.2")
    )
    PARTNER_QUALITY_RECOVER_REJECT_RATE = float(
        os.getenv("PARTNER_QUALITY_RECOVER_REJECT_RATE", "0.1")
    )
    PARTNER_QUALITY_DELTA_NEW = float(os.getenv("PARTNER_QUALITY_DELTA_NEW", "0.8"))
    PARTNER_QUALITY_DELTA_STABLE = float(
        os.getenv("PARTNER_QUALITY_DELTA_STABLE", "1.0")
    )
    PARTNER_QUALITY_DELTA_RISKY = float(
        os.getenv("PARTNER_QUALITY_DELTA_RISKY", "1.5")
    )
    PARTNER_QUALITY_DELTA_RECOVERING = float(
        os.getenv("PARTNER_QUALITY_DELTA_RECOVERING", "1.1")
    )
    EXPLORATION_RATE = float(os.getenv("EXPLORATION_RATE", "0.05"))
    EXPLORATION_BONUS = float(os.getenv("EXPLORATION_BONUS", "0.2"))
    EXPLORATION_NEW_PARTNER_REQUESTS = int(
        os.getenv("EXPLORATION_NEW_PARTNER_REQUESTS", "5")
    )
    EXPLORATION_NEW_AD_SERVES = int(os.getenv("EXPLORATION_NEW_AD_SERVES", "1"))
    EXPLORATION_MAX_AD_SERVES = int(os.getenv("EXPLORATION_MAX_AD_SERVES", "5"))
    EXPLORATION_LOOKBACK_DAYS = int(os.getenv("EXPLORATION_LOOKBACK_DAYS", "7"))
    DELIVERY_LOOKBACK_DAYS = int(os.getenv("DELIVERY_LOOKBACK_DAYS", "7"))
    DELIVERY_MIN_REQUESTS = int(os.getenv("DELIVERY_MIN_REQUESTS", "10"))
    DELIVERY_LOW_CLICK_RATE = float(os.getenv("DELIVERY_LOW_CLICK_RATE", "0.01"))
    DELIVERY_MIN_BUDGET_REMAINING_RATIO = float(
        os.getenv("DELIVERY_MIN_BUDGET_REMAINING_RATIO", "0.5")
    )
    DELIVERY_BOOST_VALUE = float(os.getenv("DELIVERY_BOOST_VALUE", "0.2"))


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
