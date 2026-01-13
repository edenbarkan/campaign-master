from app.extensions import db


class TrackingEvent(db.Model):
    __tablename__ = "tracking_events"

    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(
        db.Integer, db.ForeignKey("ad_assignments.id"), nullable=False
    )
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=False)
    ad_id = db.Column(db.Integer, db.ForeignKey("ads.id"), nullable=False)
    partner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_type = db.Column(db.String(32), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    assignment = db.relationship("AdAssignment")
    campaign = db.relationship("Campaign")
    ad = db.relationship("Ad")
    partner = db.relationship("User")
