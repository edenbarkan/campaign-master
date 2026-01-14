from decimal import Decimal, ROUND_HALF_UP

from flask import current_app, has_app_context

from app.config import Config, load_platform_fee_percent


def get_platform_fee_percent():
    value = Config.PLATFORM_FEE_PERCENT
    if has_app_context():
        value = current_app.config.get("PLATFORM_FEE_PERCENT", value)
    return load_platform_fee_percent(value)


def compute_partner_payout(max_cpc):
    fee_percent = get_platform_fee_percent()
    fee_multiplier = (Decimal("100") - fee_percent) / Decimal("100")
    payout = Decimal(str(max_cpc)) * fee_multiplier
    return payout.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
