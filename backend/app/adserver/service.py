from datetime import datetime, timezone

from sqlalchemy.orm import Session, scoped_session

from app.models import AdRequest, Wallet


def release_expired_reservations(db_session: Session, now: datetime | None = None):
    """
    Release expired reservation holds back into advertiser wallets.
    Operates inside a single transaction for idempotent cleanup runs.
    """
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    session = db_session() if isinstance(db_session, scoped_session) else db_session

    begin_transaction = (
        session.begin_nested if session.in_transaction() else session.begin
    )

    with begin_transaction():
        expired_requests = (
            session.query(AdRequest)
            .filter(
                AdRequest.status == 'active',
                AdRequest.click_tracked_at.is_(None),
                AdRequest.reserved_until < current_time,
            )
            .with_for_update()
            .all()
        )

        for ad_request in expired_requests:
            wallet = (
                session.query(Wallet)
                .filter(Wallet.user_id == ad_request.advertiser_id)
                .with_for_update()
                .one_or_none()
            )

            if wallet is None:
                ad_request.status = 'expired'
                continue

            impression_release = (
                ad_request.reserved_impression_micro
                if ad_request.impression_tracked_at is None
                else 0
            )
            click_release = (
                ad_request.reserved_click_micro
                if ad_request.click_tracked_at is None
                else 0
            )
            total_release = impression_release + click_release

            if total_release > 0:
                wallet.reserved_micro = max(
                    0,
                    wallet.reserved_micro - total_release,
                )

            ad_request.status = 'expired'
