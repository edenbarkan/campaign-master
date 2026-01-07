import uuid
from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import CheckConstraint, event, select
from sqlalchemy.sql import func
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class User(UserMixin, db.Model):
    """User model for authentication."""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_advertiser = db.Column(db.Boolean, default=False, nullable=False)
    is_publisher = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password):
        """Hash and set the password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)


class Wallet(db.Model):
    """Wallet model for user balances."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False, index=True)
    balance_micro = db.Column(db.BigInteger, default=0, nullable=False)
    reserved_micro = db.Column(db.BigInteger, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        CheckConstraint('balance_micro >= 0', name='check_balance_non_negative'),
        CheckConstraint('reserved_micro >= 0', name='check_reserved_non_negative'),
    )
    
    user = db.relationship('User', backref=db.backref('wallet', uselist=False))

    @property
    def available_micro(self):
        """Current spendable balance in micro units."""
        return self.balance_micro - self.reserved_micro


class LedgerEntry(db.Model):
    """Ledger entry model for transaction history."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    entry_type = db.Column(db.String(20), nullable=False, index=True)  # topup, spend, earn, release
    amount_micro = db.Column(db.BigInteger, nullable=False)
    ref_type = db.Column(db.String(50), nullable=True)  # e.g., 'campaign', 'ad', 'payment'
    ref_id = db.Column(db.Integer, nullable=True)  # Reference to related entity
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    user = db.relationship('User', backref=db.backref('ledger_entries', lazy='dynamic'))


class Campaign(db.Model):
    """Campaign model for advertisers."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='draft', nullable=False, index=True)  # draft, active, paused, archived
    bid_cpm_micro = db.Column(db.BigInteger, nullable=True)  # Cost per mille (1000 impressions)
    bid_cpc_micro = db.Column(db.BigInteger, nullable=True)  # Cost per click
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    user = db.relationship('User', backref=db.backref('campaigns', lazy='dynamic'))
    ads = db.relationship('Ad', backref='campaign', lazy='dynamic', cascade='all, delete-orphan')


class Ad(db.Model):
    """Ad model for campaign advertisements."""
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    landing_url = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), default='draft', nullable=False, index=True)  # draft, active, paused, archived
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Site(db.Model):
    """Site model for publishers."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    domain = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    user = db.relationship('User', backref=db.backref('sites', lazy='dynamic'))
    slots = db.relationship('Slot', backref='site', lazy='dynamic', cascade='all, delete-orphan')


class Slot(db.Model):
    """Ad slot model for publisher sites."""
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    floor_cpm_micro = db.Column(db.BigInteger, nullable=True)  # Minimum CPM bid
    floor_cpc_micro = db.Column(db.BigInteger, nullable=True)  # Minimum CPC bid
    status = db.Column(db.String(20), default='active', nullable=False, index=True)  # active, paused, archived
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        CheckConstraint('width > 0', name='check_width_positive'),
        CheckConstraint('height > 0', name='check_height_positive'),
    )


class AdRequest(db.Model):
    """Reservation request connecting advertisers to publisher inventory."""
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False, index=True)
    advertiser_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    publisher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False, index=True)
    ad_id = db.Column(db.Integer, db.ForeignKey('ad.id'), nullable=False, index=True)
    slot_id = db.Column(db.Integer, db.ForeignKey('slot.id'), nullable=False, index=True)
    price_cpm_micro = db.Column(db.BigInteger, nullable=False)
    price_cpc_micro = db.Column(db.BigInteger, nullable=False)
    reserved_impression_micro = db.Column(db.BigInteger, nullable=False)
    reserved_click_micro = db.Column(db.BigInteger, nullable=False)
    reserved_until = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    impression_tracked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    click_tracked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    status = db.Column(db.String(20), default='active', nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    advertiser = db.relationship(
        'User',
        foreign_keys=[advertiser_id],
        backref=db.backref('advertiser_ad_requests', lazy='dynamic')
    )
    publisher = db.relationship(
        'User',
        foreign_keys=[publisher_id],
        backref=db.backref('publisher_ad_requests', lazy='dynamic')
    )
    campaign = db.relationship('Campaign', backref=db.backref('ad_requests', lazy='dynamic'))
    ad = db.relationship('Ad', backref=db.backref('ad_requests', lazy='dynamic'))
    slot = db.relationship('Slot', backref=db.backref('ad_requests', lazy='dynamic'))


class Impression(db.Model):
    """Recorded impression event for an ad request."""
    id = db.Column(db.Integer, primary_key=True)
    ad_request_id = db.Column(db.Integer, db.ForeignKey('ad_request.id'), nullable=False, index=True)
    price_micro = db.Column(db.BigInteger, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    ad_request = db.relationship('AdRequest', backref=db.backref('impressions', lazy='dynamic'))


class Click(db.Model):
    """Recorded click event for an ad request."""
    id = db.Column(db.Integer, primary_key=True)
    ad_request_id = db.Column(db.Integer, db.ForeignKey('ad_request.id'), nullable=False, index=True)
    price_micro = db.Column(db.BigInteger, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    ad_request = db.relationship('AdRequest', backref=db.backref('clicks', lazy='dynamic'))


def _set_ad_request_advertiser(target, connection):
    """Ensure advertiser_id always matches the campaign owner."""
    if not target.campaign_id:
        return

    if target.campaign is not None and target.campaign.user_id is not None:
        target.advertiser_id = target.campaign.user_id
        return

    campaign_owner = connection.execute(
        select(Campaign.user_id).where(Campaign.id == target.campaign_id)
    ).scalar_one_or_none()
    if campaign_owner is not None:
        target.advertiser_id = campaign_owner


@event.listens_for(AdRequest, 'before_insert')
def ad_request_before_insert(mapper, connection, target):
    _set_ad_request_advertiser(target, connection)


@event.listens_for(AdRequest, 'before_update')
def ad_request_before_update(mapper, connection, target):
    _set_ad_request_advertiser(target, connection)
