from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

user_product_association = db.Table(
    "user_product_association",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id")),
    db.Column("product_id", db.Integer, db.ForeignKey("product.id")),
)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), index=True, unique=True)
    email = db.Column(db.String(100), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    opinions = db.relationship(
        "Opinion",
        backref="product",
        lazy="dynamic",
        cascade="all, delete, delete-orphan",
    )


class Opinion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    recommendation = db.Column(db.Boolean)
    stars = db.Column(db.Float)
    pros = db.Column(db.String(100))
    cons = db.Column(db.String(100))
