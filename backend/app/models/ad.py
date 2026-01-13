from app.extensions import db


class Ad(db.Model):
    __tablename__ = "ads"

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    destination_url = db.Column(db.String(500), nullable=False)
    active = db.Column(db.Boolean, nullable=False, server_default="true")
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    campaign = db.relationship("Campaign", backref="ads")
