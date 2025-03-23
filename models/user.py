from app import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    mobile = db.Column(db.String(15))
    
    # Relationships
    owned_bikes = db.relationship('Bike', backref=db.backref('owner_user', lazy=True), 
                                foreign_keys='Bike.owner_id')
    purchases_made = db.relationship('Purchase', foreign_keys='Purchase.buyer_id', 
                                   backref=db.backref('buyer_user', lazy=True))
    purchases_sold = db.relationship('Purchase', foreign_keys='Purchase.seller_id', 
                                   backref=db.backref('seller_user', lazy=True))
    rentals_given = db.relationship('Rental', foreign_keys='Rental.owner_id', 
                                  backref='owner', lazy=True)
    rentals_taken = db.relationship('Rental', foreign_keys='Rental.renter_id', 
                                  backref='renter', lazy=True)

    def __init__(self, username, email, password_hash, mobile=None):
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.mobile = mobile