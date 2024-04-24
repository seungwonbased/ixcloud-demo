from . import db


class Dummies(db.Model):
    dummy_id = db.Column(db.Integer, primary_key=True)
    dummy = db.Column(db.String(200), nullable=False)