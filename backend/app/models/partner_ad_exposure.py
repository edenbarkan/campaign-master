from app.extensions import db


class PartnerAdExposure(db.Model):
    __tablename__ = "partner_ad_exposures"

    id = db.Column(db.Integer, primary_key=True)
    partner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    ad_id = db.Column(db.Integer, db.ForeignKey("ads.id"), nullable=False)
    last_served_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    __table_args__ = (
        db.UniqueConstraint("partner_id", "ad_id", name="uq_partner_ad_exposure"),
    )

    partner = db.relationship("User")
    ad = db.relationship("Ad")
