from datetime import datetime
from database import db

class Bike(db.Model):
    __tablename__ = 'bike'
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Basic Details
    brand = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    engine_cc = db.Column(db.Integer, nullable=False)
    km_driven = db.Column(db.Integer, nullable=False)
    mileage = db.Column(db.Float, nullable=False)
    condition = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    # Listing Details
    listing_type = db.Column(db.String(10), nullable=False)  # 'rent' or 'sale'
    price_per_day = db.Column(db.Float, nullable=True)
    sale_price = db.Column(db.Float, nullable=True)
    is_available = db.Column(db.Boolean, default=True)
    
    # Owner Information
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Images
    image_url_1 = db.Column(db.String(200), nullable=True)
    image_url_2 = db.Column(db.String(200), nullable=True)
    image_url_3 = db.Column(db.String(200), nullable=True)
    
    # Form-specific metadata
    suggested_price = db.Column(db.Float, nullable=True)
    last_price_calculation = db.Column(db.DateTime, nullable=True)
    image_1_original_name = db.Column(db.String(200), nullable=True)
    image_2_original_name = db.Column(db.String(200), nullable=True)
    image_3_original_name = db.Column(db.String(200), nullable=True)
    image_1_size = db.Column(db.Integer, nullable=True)  # in bytes
    image_2_size = db.Column(db.Integer, nullable=True)  # in bytes
    image_3_size = db.Column(db.Integer, nullable=True)  # in bytes
    form_submission_ip = db.Column(db.String(45), nullable=True)  # IPv6 compatible
    form_submission_user_agent = db.Column(db.String(500), nullable=True)
    last_updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    rentals = db.relationship('Rental', backref='bike', lazy=True)
    rental_requests = db.relationship('RentalRequest', backref='bike', lazy=True)
    bike_purchases = db.relationship('Purchase', backref=db.backref('bike_details', lazy=True))
    
    def __repr__(self):
        return f'<Bike {self.brand} {self.model} ({self.year})>'
    
    def to_dict(self):
        """Convert bike object to dictionary"""
        return {
            'id': self.id,
            'brand': self.brand,
            'model': self.model,
            'year': self.year,
            'engine_cc': self.engine_cc,
            'km_driven': self.km_driven,
            'mileage': self.mileage,
            'condition': self.condition,
            'description': self.description,
            'listing_type': self.listing_type,
            'price_per_day': self.price_per_day,
            'sale_price': self.sale_price,
            'is_available': self.is_available,
            'owner_id': self.owner_id,
            'images': [
                self.image_url_1,
                self.image_url_2,
                self.image_url_3
            ],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_updated_at': self.last_updated_at.isoformat() if self.last_updated_at else None,
            'suggested_price': self.suggested_price
        }


