from datetime import datetime, timedelta

from app.models.click_event import ClickEvent


def _click_decisions(partner_id, cutoff):
    accepted = (
        ClickEvent.query.filter_by(partner_id=partner_id, status="ACCEPTED")
        .filter(ClickEvent.ts >= cutoff)
        .count()
    )
    rejected = (
        ClickEvent.query.filter_by(partner_id=partner_id, status="REJECTED")
        .filter(ClickEvent.ts >= cutoff)
        .count()
    )
    return accepted, rejected


def partner_reject_rate(partner_id, lookback_days):
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    accepted, rejected = _click_decisions(partner_id, cutoff)
    total = accepted + rejected
    return rejected / total if total else 0


def partner_quality_state(
    partner_id,
    recent_days,
    long_days,
    new_clicks_threshold,
    risky_reject_rate,
    recovering_reject_rate,
    delta_multipliers,
):
    now = datetime.utcnow()
    recent_cutoff = now - timedelta(days=recent_days)
    long_cutoff = now - timedelta(days=long_days)

    recent_accepted, recent_rejected = _click_decisions(partner_id, recent_cutoff)
    long_accepted, long_rejected = _click_decisions(partner_id, long_cutoff)

    recent_total = recent_accepted + recent_rejected
    long_total = long_accepted + long_rejected

    recent_rate = recent_rejected / recent_total if recent_total else 0
    long_rate = long_rejected / long_total if long_total else 0

    if long_total < new_clicks_threshold:
        state = "NEW"
        note = "Limited history; penalties softened until more data arrives."
    elif recent_rate >= risky_reject_rate:
        state = "RISKY"
        note = "Recent reject rate elevated; quality penalty intensified."
    elif long_rate >= risky_reject_rate and recent_rate <= recovering_reject_rate:
        state = "RECOVERING"
        note = "Rejects are improving; penalty easing as quality recovers."
    else:
        state = "STABLE"
        note = "Consistent quality; standard penalty applies."

    delta_multiplier = delta_multipliers.get(state, 1.0)

    return {
        "state": state,
        "note": note,
        "recent_reject_rate": recent_rate,
        "long_reject_rate": long_rate,
        "clicks": long_total,
        "delta_multiplier": delta_multiplier,
    }
