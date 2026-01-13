from app.extensions import db


class AdAssignment(db.Model):
    __tablename__ = "ad_assignments"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    partner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=False)
    ad_id = db.Column(db.Integer, db.ForeignKey("ads.id"), nullable=False)
    category = db.Column(db.String(120))
    geo = db.Column(db.String(120))
    placement = db.Column(db.String(120))
    device = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    campaign = db.relationship("Campaign")
    ad = db.relationship("Ad")
    partner = db.relationship("User")
