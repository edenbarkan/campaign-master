from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256

from flask import current_app, request

from app.extensions import db
from app.models.click_event import ClickEvent


@dataclass
class ClickDecision:
    status: str
    reason: str | None
    ip_hash: str
    ua_hash: str | None


class ClickRateLimiter:
    def __init__(self):
        self._buckets = {}

    def allow(self, ip_hash, now_ts, limit, window_seconds=60):
        timestamps = self._buckets.get(ip_hash, [])
        cutoff = now_ts - window_seconds
        timestamps = [ts for ts in timestamps if ts >= cutoff]
        if len(timestamps) >= limit:
            self._buckets[ip_hash] = timestamps
            return False
        timestamps.append(now_ts)
        self._buckets[ip_hash] = timestamps
        return True


_rate_limiter = ClickRateLimiter()


def get_hash_salt():
    return current_app.config.get("CLICK_HASH_SALT", "devsalt")


def hash_value(value, salt=None):
    if salt is None:
        salt = get_hash_salt()
    payload = f"{salt}:{value}".encode("utf-8")
    return sha256(payload).hexdigest()


def get_request_ip(req):
    forwarded = req.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return req.remote_addr or ""


def build_request_fingerprint(req):
    ip = get_request_ip(req)
    ua = req.headers.get("User-Agent", "") or ""
    ip_hash = hash_value(ip)
    ua_hash = hash_value(ua) if ua else None
    return ip_hash, ua_hash, ua


def _is_duplicate_click(assignment_code, ip_hash, now_dt):
    window_seconds = current_app.config.get("CLICK_DUPLICATE_WINDOW_SECONDS", 10)
    cutoff = now_dt - timedelta(seconds=window_seconds)
    existing = (
        db.session.query(ClickEvent.id)
        .filter(ClickEvent.assignment_code == assignment_code)
        .filter(ClickEvent.ip_hash == ip_hash)
        .filter(ClickEvent.ts >= cutoff)
        .first()
    )
    return existing is not None


def _rate_limit_allows(ip_hash, now_dt):
    limit = current_app.config.get("CLICK_RATE_LIMIT_PER_MINUTE", 20)
    return _rate_limiter.allow(ip_hash, now_dt.timestamp(), limit, window_seconds=60)


def validate_click(assignment):
    ip_hash, ua_hash, ua = build_request_fingerprint(request)

    if assignment is None:
        return ClickDecision(
            status="REJECTED",
            reason="INVALID_ASSIGNMENT",
            ip_hash=ip_hash,
            ua_hash=ua_hash,
        )

    if not ua.strip():
        return ClickDecision(
            status="REJECTED",
            reason="BOT_SUSPECTED",
            ip_hash=ip_hash,
            ua_hash=ua_hash,
        )

    now_dt = datetime.utcnow()
    if _is_duplicate_click(assignment.code, ip_hash, now_dt):
        return ClickDecision(
            status="REJECTED",
            reason="DUPLICATE_CLICK",
            ip_hash=ip_hash,
            ua_hash=ua_hash,
        )

    if not _rate_limit_allows(ip_hash, now_dt):
        return ClickDecision(
            status="REJECTED",
            reason="RATE_LIMIT",
            ip_hash=ip_hash,
            ua_hash=ua_hash,
        )

    return ClickDecision(
        status="ACCEPTED",
        reason=None,
        ip_hash=ip_hash,
        ua_hash=ua_hash,
    )
