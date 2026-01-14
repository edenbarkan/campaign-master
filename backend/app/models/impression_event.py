from app.extensions import db


class ImpressionEvent(db.Model):
    __tablename__ = "impression_events"

    id = db.Column(db.Integer, primary_key=True)
    assignment_code = db.Column(db.String(64), nullable=False, index=True)
    partner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"))
    ad_id = db.Column(db.Integer, db.ForeignKey("ads.id"))
    ts = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    ip_hash = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(16), nullable=False)
    dedup_reason = db.Column(db.String(32))

    campaign = db.relationship("Campaign")
    ad = db.relationship("Ad")
    partner = db.relationship("User")
