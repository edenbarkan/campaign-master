from app.extensions import db


class PartnerAdRequestEvent(db.Model):
    __tablename__ = "partner_ad_request_events"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    partner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    placement = db.Column(db.String(120))
    device = db.Column(db.String(120))
    geo = db.Column(db.String(120))
    category = db.Column(db.String(120))
    filled = db.Column(db.Boolean, nullable=False, server_default="false")
    ad_id = db.Column(db.Integer, db.ForeignKey("ads.id"))
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"))
    assignment_code = db.Column(db.String(64))
    explanation = db.Column(db.Text)
    score_breakdown = db.Column(db.Text)

    partner = db.relationship("User")
    ad = db.relationship("Ad")
    campaign = db.relationship("Campaign")
