from app.extensions import db


class Campaign(db.Model):
    __tablename__ = "campaigns"

    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(32), nullable=False, default="active")
    budget_total = db.Column(db.Numeric(12, 2), nullable=False)
    budget_spent = db.Column(db.Numeric(12, 2), nullable=False, server_default="0")
    buyer_cpc = db.Column(db.Numeric(12, 2), nullable=False)
    partner_payout = db.Column(db.Numeric(12, 2), nullable=False)
    targeting_category = db.Column(db.String(120))
    targeting_geo = db.Column(db.String(120))
    targeting_device = db.Column(db.String(120))
    targeting_placement = db.Column(db.String(120))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    buyer = db.relationship("User", backref="campaigns")

    @property
    def budget_remaining(self):
        return (self.budget_total or 0) - (self.budget_spent or 0)

    @property
    def max_cpc(self):
        return self.buyer_cpc

    @max_cpc.setter
    def max_cpc(self, value):
        self.buyer_cpc = value
