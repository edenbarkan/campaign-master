from app.extensions import db


class ClickEvent(db.Model):
    __tablename__ = "click_events"

    id = db.Column(db.Integer, primary_key=True)
    assignment_code = db.Column(db.String(64), nullable=False, index=True)
    partner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"))
    ad_id = db.Column(db.Integer, db.ForeignKey("ads.id"))
    ts = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    ip_hash = db.Column(db.String(64), nullable=False)
    ua_hash = db.Column(db.String(64))
    status = db.Column(db.String(16), nullable=False)
    reject_reason = db.Column(db.String(32))
    spend_delta = db.Column(db.Numeric(12, 2), nullable=False, server_default="0")
    earnings_delta = db.Column(db.Numeric(12, 2), nullable=False, server_default="0")
    profit_delta = db.Column(db.Numeric(12, 2), nullable=False, server_default="0")

    campaign = db.relationship("Campaign")
    ad = db.relationship("Ad")
    partner = db.relationship("User")
