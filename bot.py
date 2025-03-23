from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# MongoDB connection
MONGO_URI = os.getenv('MONGO_URI', 'mongodb+srv://kr4785543:1234567890@cluster0.220yz.mongodb.net/')
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client['bike_rental']
bikes_collection = mongo_db['bikes']

# SQLAlchemy setup (needed only for username lookups)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///bikerental.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Minimal User model for username lookups
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)

@app.route('/api/bikes/search', methods=['GET'])
def search_bikes():
    try:
        # Get query parameters with defaults
        name = request.args.get('name', '').strip()
        model = request.args.get('model', '').strip()
        year = request.args.get('year', type=int)
        price_low = request.args.get('price_low', type=float, default=0)
        price_high = request.args.get('price_high', type=float)

        # Build MongoDB query
        query = {'is_available': True}
        
        # Add filters if parameters are provided
        if name:
            query['name'] = {'$regex': name, '$options': 'i'}  # case-insensitive search
        if model:
            query['model'] = {'$regex': model, '$options': 'i'}
        if year:
            query['year'] = year
            
        # Price filter for both rental and sale listings
        if price_high or price_low > 0:
            price_query = []
            if price_high:
                price_query.append({
                    'listing_type': 'rent',
                    'price_per_day': {'$gte': price_low, '$lte': price_high}
                })
                price_query.append({
                    'listing_type': 'sale',
                    'sale_price': {'$gte': price_low, '$lte': price_high}
                })
            else:
                price_query.append({
                    'listing_type': 'rent',
                    'price_per_day': {'$gte': price_low}
                })
                price_query.append({
                    'listing_type': 'sale',
                    'sale_price': {'$gte': price_low}
                })
            query['$or'] = price_query

        # Execute MongoDB query
        bikes = bikes_collection.find(query)

        # Format results
        results = []
        for bike in bikes:
            try:
                username = User.query.get(bike['owner_id']).username
            except:
                username = "Unknown"  # Fallback if user not found
                
            results.append({
                'id': bike['sql_id'],
                'name': bike['name'],
                'model': bike['model'],
                'year': bike['year'],
                'condition': bike['condition'],
                'listing_type': bike['listing_type'],
                'price_per_day': bike['price_per_day'],
                'sale_price': bike['sale_price'],
                'is_available': bike['is_available'],
                'owner': {
                    'id': bike['owner_id'],
                    'username': username
                },
                'images': bike.get('images', []),
                'metadata': bike.get('metadata', {
                    'views': 0,
                    'favorites': 0
                })
            })

        return jsonify({
            'status': 'success',
            'count': len(results),
            'bikes': results
        }), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5002))
    with app.app_context():
        db.create_all()  # Create SQLite database and tables
    app.run(host='0.0.0.0', port=port)