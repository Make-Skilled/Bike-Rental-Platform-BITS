from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
from dotenv import load_dotenv
from datetime import datetime
import os
from werkzeug.utils import secure_filename

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bikerental.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Mail settings
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

# Initialize extensions
db = SQLAlchemy(app)
mail = Mail(app)

def send_email(to, subject, body):
    if not app.config['MAIL_USERNAME'] or not app.config['MAIL_PASSWORD']:
        print(f"Email not sent (mail not configured) - To: {to}, Subject: {subject}")
        return True
    try:
        msg = Message(
            subject=subject,
            recipients=[to],
            body=body
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

# Add configurations for image uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'bike_images')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@app.route('/static/<path:filename>')
def serve_static(filename):
    if filename.startswith('bike_images/'):
        # For bike images, serve from the bike_images subdirectory
        image_filename = filename.split('/')[-1]
        return send_from_directory(app.config['UPLOAD_FOLDER'], image_filename)
    # For other static files
    return send_from_directory('static', filename)

def save_image(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        return os.path.join('bike_images', filename)  # Return relative path
    return None

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    mobile = db.Column(db.String(15))
    owned_bikes = db.relationship('Bike', backref=db.backref('owner_user', lazy=True), foreign_keys='Bike.owner_id')
    purchases_made = db.relationship('Purchase', foreign_keys='Purchase.buyer_id', backref=db.backref('buyer_user', lazy=True))
    purchases_sold = db.relationship('Purchase', foreign_keys='Purchase.seller_id', backref=db.backref('seller_user', lazy=True))
    rentals_given = db.relationship('Rental', foreign_keys='Rental.owner_id', backref='owner', lazy=True)
    rentals_taken = db.relationship('Rental', foreign_keys='Rental.renter_id', backref='renter', lazy=True)
    # Relationship is defined in RentalRequest model

# Bike Model
class Bike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    name = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    condition = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    listing_type = db.Column(db.String(10), nullable=False)  # 'rent' or 'sale'
    price_per_day = db.Column(db.Float, nullable=True)
    sale_price = db.Column(db.Float, nullable=True)
    image_url_1 = db.Column(db.String(200))
    image_url_2 = db.Column(db.String(200))
    image_url_3 = db.Column(db.String(200))
    rentals = db.relationship('Rental', backref='bike', lazy=True)
    rental_requests = db.relationship('RentalRequest', backref='bike', lazy=True)
    bike_purchases = db.relationship('Purchase', backref=db.backref('bike_details', lazy=True))

# Rental Model
class Rental(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bike_id = db.Column(db.Integer, db.ForeignKey('bike.id'), nullable=False)
    renter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, active, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Rental Request Model
class RentalRequest(db.Model):
    __tablename__ = 'rental_request'
    id = db.Column(db.Integer, primary_key=True)
    bike_id = db.Column(db.Integer, db.ForeignKey('bike.id'), nullable=False)
    renter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    renter = db.relationship('User', foreign_keys=[renter_id], backref=db.backref('rental_requests_made', lazy=True))

# Purchase Model
class Purchase(db.Model):
    __tablename__ = 'purchase'
    id = db.Column(db.Integer, primary_key=True)
    bike_id = db.Column(db.Integer, db.ForeignKey('bike.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    price = db.Column(db.Float, nullable=False)
    message = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please login first')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Context processor to add pending requests count to all templates
@app.context_processor
def utility_processor():
    def get_pending_requests_count():
        if not session.get('user_id'):
            return 0
        # Count pending requests for bikes owned by the current user
        return RentalRequest.query.join(Bike).filter(
            Bike.owner_id == session['user_id'],
            RentalRequest.status == 'pending'
        ).count()
    return dict(pending_requests_count=get_pending_requests_count())

def send_notification_email(subject, recipient, template, **kwargs):
    try:
        msg = Message(
            subject,
            recipients=[recipient]
        )
        msg.html = render_template(template, **kwargs)
        mail.send(msg)
        print(f"Email sent successfully to {recipient}")
    except Exception as e:
        print(f"Failed to send email: {str(e)}")

@app.route('/')
def index():
    bikes = Bike.query.filter_by(is_available=True).order_by(Bike.created_at.desc()).all()
    return render_template('index.html', bikes=bikes)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))

        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))

        # Create new user
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, mobile=mobile, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Welcome back!')
            return redirect(url_for('index'))
        
        flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out')
    return redirect(url_for('index'))

# Bike Management Routes
@app.route('/bikes/add', methods=['GET', 'POST'])
@login_required
def add_bike():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            model = request.form.get('model')
            year = request.form.get('year')
            condition = request.form.get('condition')
            listing_type = request.form.get('listing_type')
            if listing_type == 'rent':
                price_per_day = float(request.form.get('price_per_day'))
                sale_price = None
            elif listing_type == 'sale':
                price_per_day = None
                sale_price = float(request.form.get('sale_price'))
            else:
                flash('Invalid listing type', 'danger')
                return redirect(url_for('add_bike'))
            
            description = request.form.get('description')

            # Handle image uploads
            image_urls = []
            for i in range(1, 4):
                image = request.files.get(f'image{i}')
                if image and allowed_file(image.filename):
                    filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{image.filename}")
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    image_urls.append(os.path.join('bike_images', filename))  # Store the relative path
                else:
                    image_urls.append(None)

            new_bike = Bike(
                name=name,
                model=model,
                year=year,
                condition=condition,
                listing_type=listing_type,
                price_per_day=price_per_day,
                sale_price=sale_price,
                description=description,
                owner_id=session['user_id'],
                image_url_1=image_urls[0],
                image_url_2=image_urls[1],
                image_url_3=image_urls[2]
            )

            db.session.add(new_bike)
            db.session.commit()
            flash('Bike added successfully!', 'success')
            return redirect(url_for('my_bikes'))

        except Exception as e:
            print(f"Error adding bike: {str(e)}")
            db.session.rollback()
            flash('Error adding bike. Please try again.', 'danger')
            return redirect(url_for('add_bike'))

    return render_template('add_bike.html')

@app.route('/bikes/my-bikes')
@login_required
def my_bikes():
    user = User.query.get(session['user_id'])
    return render_template('my_bikes.html', bikes=user.owned_bikes)

@app.route('/bikes/<int:bike_id>')
def view_bike(bike_id):
    bike = Bike.query.get_or_404(bike_id)
    # Get current and future rentals for this bike
    current_time = datetime.utcnow()
    active_rentals = Rental.query.filter(
        Rental.bike_id == bike_id,
        Rental.status == 'active',
        Rental.end_date > current_time
    ).order_by(Rental.start_date).all()
    
    # Get pending rental requests
    pending_requests = RentalRequest.query.filter(
        RentalRequest.bike_id == bike_id,
        RentalRequest.status == 'pending'
    ).order_by(RentalRequest.created_at).all()
    
    return render_template('view_bike.html', 
                           bike=bike, 
                           active_rentals=active_rentals,
                           pending_requests=pending_requests,
                           current_time=current_time)

@app.route('/bikes/<int:bike_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_bike(bike_id):
    bike = Bike.query.get_or_404(bike_id)
    
    # Check if the current user is the owner
    if bike.owner_id != session['user_id']:
        flash('You can only edit your own bikes.', 'danger')
        return redirect(url_for('my_bikes'))
    
    if request.method == 'POST':
        try:
            bike.name = request.form.get('name')
            bike.model = request.form.get('model')
            bike.year = request.form.get('year')
            bike.condition = request.form.get('condition')
            bike.description = request.form.get('description')
            bike.listing_type = request.form.get('listing_type')
            bike.is_available = 'is_available' in request.form
            
            # Handle prices based on listing type
            if bike.listing_type == 'rent':
                price_per_day = request.form.get('price_per_day')
                bike.price_per_day = float(price_per_day) if price_per_day else None
                bike.sale_price = None
            else:
                sale_price = request.form.get('sale_price')
                bike.sale_price = float(sale_price) if sale_price else None
                bike.price_per_day = None
            
            # Handle image uploads
            for i in range(1, 4):
                image = request.files.get(f'image{i}')
                if image and allowed_file(image.filename):
                    filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{image.filename}")
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    setattr(bike, f'image_url_{i}', os.path.join('bike_images', filename))

            db.session.commit()
            flash('Bike updated successfully!', 'success')
            return redirect(url_for('my_bikes'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating bike: {str(e)}")
            flash('Error updating bike. Please try again.', 'danger')
            return redirect(url_for('edit_bike', bike_id=bike_id))
    
    return render_template('edit_bike.html', bike=bike)

@app.route('/bikes/<int:bike_id>/delete')
@login_required
def delete_bike(bike_id):
    bike = Bike.query.get_or_404(bike_id)
    if bike.owner_id != session['user_id']:
        flash('You can only delete your own bikes')
        return redirect(url_for('my_bikes'))
    
    try:
        db.session.delete(bike)
        db.session.commit()
        flash('Bike deleted successfully!')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting bike. Please try again.')
    
    return redirect(url_for('my_bikes'))

@app.route('/bikes/<int:bike_id>/rent', methods=['GET', 'POST'])
@login_required
def rent_bike(bike_id):
    return redirect(url_for('request_rental', bike_id=bike_id))

@app.route('/bikes/<int:bike_id>/request-rental', methods=['GET', 'POST'])
@login_required
def request_rental(bike_id):
    bike = Bike.query.get_or_404(bike_id)
    
    if request.method == 'POST':
        if bike.owner_id == session['user_id']:
            flash('You cannot request to rent your own bike')
            return redirect(url_for('view_bike', bike_id=bike_id))
            
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
        message = request.form.get('message', '')
        
        if start_date >= end_date:
            flash('End date must be after start date')
            return redirect(url_for('request_rental', bike_id=bike_id))
            
        if not bike.is_available:
            flash('This bike is not available for the selected dates')
            return redirect(url_for('view_bike', bike_id=bike_id))
            
        print(f"Creating rental request for bike {bike_id} from user {session['user_id']}")
        rental_request = RentalRequest(
            bike_id=bike_id,
            renter_id=session['user_id'],
            start_date=start_date,
            end_date=end_date,
            message=message,
            status='pending'
        )
        
        db.session.add(rental_request)
        db.session.commit()
        print(f"Rental request {rental_request.id} created successfully")
        
        if bike.owner_user.email:
            send_notification_email(
                'New Rental Request',
                bike.owner_user.email,
                'email/new_request.html',
                user=User.query.get(session['user_id']),
                bike=bike,
                request=rental_request
            )
        
        flash('Your rental request has been sent! The owner will review it and respond soon.')
        return redirect(url_for('my_rental_requests'))
        
    return render_template('request_rental.html', bike=bike, today=datetime.now().strftime('%Y-%m-%d'))

@app.route('/bikes/purchase/<int:bike_id>', methods=['POST'])
@login_required
def request_purchase(bike_id):
    bike = Bike.query.get_or_404(bike_id)
    
    if not bike.is_available:
        flash('Sorry, this bike is no longer available.', 'danger')
        return redirect(url_for('view_bike', bike_id=bike_id))
        
    if bike.owner_id == session['user_id']:
        flash('You cannot purchase your own bike.', 'danger')
        return redirect(url_for('view_bike', bike_id=bike_id))
        
    if bike.listing_type != 'sale':
        flash('This bike is not listed for sale.', 'danger')
        return redirect(url_for('view_bike', bike_id=bike_id))
    
    # Check if user already has a pending request for this bike
    existing_request = Purchase.query.filter_by(
        bike_id=bike_id,
        buyer_id=session['user_id'],
        status='pending'
    ).first()
    
    if existing_request:
        flash('You already have a pending request for this bike.', 'info')
        return redirect(url_for('view_bike', bike_id=bike_id))
    
    try:
        buyer = User.query.get(session['user_id'])
        seller = bike.owner_user
        message = request.form.get('message', '')
        
        # Create a new purchase request
        purchase = Purchase(
            bike_id=bike_id,
            buyer_id=session['user_id'],
            seller_id=bike.owner_id,
            price=bike.sale_price,
            message=message
        )
        
        db.session.add(purchase)
        db.session.commit()
        
        # Send email notifications
        send_email(
            to=buyer.email,
            subject=f"Purchase Request Sent - {bike.name}",
            body=f"""Hi {buyer.username},

Your purchase request has been sent for {bike.name}.

Bike Details:
- Name: {bike.name}
- Model: {bike.model}
- Year: {bike.year}
- Price: ${bike.sale_price}

Seller Details:
- Name: {seller.username}
- Contact: {seller.mobile if seller.mobile else 'Not provided'}

Your message to the seller:
{message}

The seller will review your request and contact you if they accept.

Best regards,
The Bike Rental Team"""
        )
        
        send_email(
            to=seller.email,
            subject=f"New Purchase Request - {bike.name}",
            body=f"""Hi {seller.username},

{buyer.username} is interested in buying your bike {bike.name}.

Buyer Details:
- Name: {buyer.username}
- Contact: {buyer.mobile if buyer.mobile else 'Not provided'}

Their message:
{message}

Please review this request in your dashboard and accept or reject it.

Best regards,
The Bike Rental Team"""
        )
        
        flash('Your purchase request has been sent! You will be notified when the seller responds.', 'success')
        return redirect(url_for('my_purchase_requests'))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error processing purchase request: {str(e)}")
        flash('Error processing your request. Please try again.', 'danger')
        return redirect(url_for('view_bike', bike_id=bike_id))

@app.route('/my-purchase-requests')
@login_required
def my_purchase_requests():
    # Get requests for bikes I'm selling
    selling_requests = Purchase.query.join(Bike).filter(
        Bike.owner_id == session['user_id'],
        Purchase.status == 'pending'
    ).all()
    
    # Get my requests to buy bikes
    buying_requests = Purchase.query.filter_by(
        buyer_id=session['user_id']
    ).all()
    
    return render_template(
        'my_purchase_requests.html',
        selling_requests=selling_requests,
        buying_requests=buying_requests
    )

@app.route('/handle-purchase-request/<int:request_id>', methods=['POST'])
@login_required
def handle_purchase_request(request_id):
    purchase = Purchase.query.get_or_404(request_id)
    bike = Bike.query.get_or_404(purchase.bike_id)
    
    # Verify the current user is the seller
    if bike.owner_id != session['user_id']:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('my_purchase_requests'))
    
    action = request.form.get('action')
    if action not in ['accept', 'reject']:
        flash('Invalid action.', 'danger')
        return redirect(url_for('my_purchase_requests'))
    
    try:
        if action == 'accept':
            # Mark the purchase as accepted
            purchase.status = 'accepted'
            purchase.seller_id = session['user_id']  # Set the seller_id
            # Mark the bike as unavailable
            bike.is_available = False
            # Reject all other pending requests for this bike
            other_requests = Purchase.query.filter(
                Purchase.bike_id == bike.id,
                Purchase.id != purchase.id,
                Purchase.status == 'pending'
            ).all()
            for req in other_requests:
                req.status = 'rejected'
                # Send rejection email
                send_email(
                    to=req.buyer_user.email,
                    subject=f"Purchase Request Rejected - {bike.name}",
                    body=f"""Hi {req.buyer_user.username},

Unfortunately, your purchase request for {bike.name} was not accepted as the bike has been sold to another buyer.

You can continue browsing other available bikes on our platform.

Best regards,
The Bike Rental Team"""
                )
            
            # Send acceptance email
            send_email(
                to=purchase.buyer_user.email,
                subject=f"Purchase Request Accepted - {bike.name}",
                body=f"""Hi {purchase.buyer_user.username},

Great news! {bike.owner_user.username} has accepted your purchase request for {bike.name}.

Seller Contact:
{bike.owner_user.mobile if bike.owner_user.mobile else 'Not provided'}

Please contact the seller to arrange the payment and pickup.

Best regards,
The Bike Rental Team"""
            )
            
            # Send notification to seller
            send_email(
                to=bike.owner_user.email,
                subject=f"You've Accepted a Purchase Request - {bike.name}",
                body=f"""Hi {bike.owner_user.username},

You have accepted the purchase request from {purchase.buyer_user.username} for your bike {bike.name}.

Buyer Contact:
{purchase.buyer_user.mobile if purchase.buyer_user.mobile else 'Not provided'}

Please wait for the buyer to contact you to arrange the payment and pickup.

Best regards,
The Bike Rental Team"""
            )
            
        else:  # reject
            purchase.status = 'rejected'
            purchase.seller_id = session['user_id']  # Set the seller_id
            send_email(
                to=purchase.buyer_user.email,
                subject=f"Purchase Request Rejected - {bike.name}",
                body=f"""Hi {purchase.buyer_user.username},

Unfortunately, your purchase request for {bike.name} was not accepted.

You can continue browsing other available bikes on our platform.

Best regards,
The Bike Rental Team"""
            )
        
        db.session.commit()
        flash(f'Purchase request {action}ed successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"Error handling purchase request: {str(e)}")
        flash('Error processing your request. Please try again.', 'danger')
    
    return redirect(url_for('my_purchase_requests'))

@app.route('/rentals/my-rentals')
@login_required
def my_rentals():
    # Get rentals where user is the renter
    my_rentals = Rental.query.filter_by(
        renter_id=session['user_id']
    ).order_by(Rental.created_at.desc()).all()
    
    # Get rentals of bikes owned by the user
    owned_bikes = Bike.query.filter_by(owner_id=session['user_id']).with_entities(Bike.id).all()
    owned_bike_ids = [bike[0] for bike in owned_bikes]
    rentals_of_my_bikes = Rental.query.filter(
        Rental.bike_id.in_(owned_bike_ids)
    ).order_by(Rental.created_at.desc()).all()
    
    return render_template('my_rentals.html', 
                         my_rentals=my_rentals,
                         rentals_of_my_bikes=rentals_of_my_bikes)

@app.route('/rentals/<int:rental_id>/status', methods=['POST'])
@login_required
def update_rental_status(rental_id):
    rental = Rental.query.get_or_404(rental_id)
    
    if rental.renter_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    new_status = data.get('status')
    
    if new_status not in ['pending', 'active', 'completed', 'cancelled']:
        return jsonify({'error': 'Invalid status'}), 400
    
    rental.status = new_status
    if new_status in ['completed', 'cancelled']:
        rental.bike.is_available = True
    
    db.session.commit()
    return jsonify({'message': 'Status updated successfully'}), 200

@app.route('/rentals/<int:rental_id>/complete', methods=['POST'])
@login_required
def complete_rental(rental_id):
    rental = Rental.query.get_or_404(rental_id)
    
    # Verify that the current user is the bike owner
    if rental.bike.owner_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Only active rentals can be marked as complete
    if rental.status != 'active':
        return jsonify({'error': 'Only active rentals can be marked as complete'}), 400
    
    try:
        rental.status = 'completed'
        rental.bike.is_available = True  # Make the bike available again
        db.session.commit()
        return jsonify({'message': 'Rental marked as complete successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/my-rental-requests')
@login_required
def my_rental_requests():
    user_id = session['user_id']
    
    sent_requests = RentalRequest.query.filter_by(renter_id=user_id).order_by(RentalRequest.created_at.desc()).all()
    
    owned_bikes_info = db.session.execute("""
        SELECT b.id, b.name, 
               (SELECT COUNT(*) FROM rental_request WHERE bike_id = b.id) as request_count
        FROM bike b 
        WHERE b.owner_id = :user_id
    """, {'user_id': user_id}).fetchall()
    
    owned_bike_ids = [bike.id for bike in Bike.query.filter_by(owner_id=user_id).all()]
    
    received_requests = RentalRequest.query.filter(
        RentalRequest.bike_id.in_(owned_bike_ids) if owned_bike_ids else False
    ).order_by(RentalRequest.created_at.desc()).all()
    
    return render_template('my_rental_requests.html', 
                         sent_requests=sent_requests,
                         received_requests=received_requests)

@app.route('/rental-requests/<int:request_id>/handle', methods=['POST'])
@login_required
def handle_rental_request(request_id):
    rental_request = RentalRequest.query.get_or_404(request_id)
    bike = rental_request.bike
    
    if bike.owner_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
        
    action = request.form.get('action')
    if action not in ['approve', 'reject']:
        return jsonify({'error': 'Invalid action'}), 400
    
    if rental_request.status != 'pending':
        return jsonify({'error': 'Request has already been processed'}), 400
        
    requester = User.query.get(rental_request.renter_id)
    
    if action == 'approve':
        # Calculate rental duration and total price
        rental_days = (rental_request.end_date - rental_request.start_date).days
        total_price = rental_days * bike.price_per_day
        
        # Create a new rental with status 'active'
        rental = Rental(
            bike_id=bike.id,
            renter_id=rental_request.renter_id,
            owner_id=bike.owner_id,
            start_date=rental_request.start_date,
            end_date=rental_request.end_date,
            total_price=total_price,
            status='active'  # Explicitly set status to active
        )
        
        # Update bike and request status
        bike.is_available = False
        rental_request.status = 'approved'
        
        # Add and commit the rental
        db.session.add(rental)
        db.session.commit()
        
        print(f"Created rental {rental.id} with status: {rental.status}")
        
        if requester.email:
            send_notification_email(
                'Your Rental Request was Approved!',
                requester.email,
                'email/request_approved.html',
                user=requester,
                bike=bike,
                request=rental_request,
                rental=rental
            )
        
    else:  # reject
        rental_request.status = 'rejected'
        if requester.email:
            send_notification_email(
                'Update on Your Rental Request',
                requester.email,
                'email/request_rejected.html',
                user=requester,
                bike=bike,
                request=rental_request
            )
        db.session.commit()
    
    return jsonify({'message': f'Request {action}d successfully'})

def send_purchase_confirmation_email(purchase):
    buyer_email = purchase.buyer_user.email
    seller_email = purchase.seller_user.email
    bike_name = purchase.bike_details.name
    
    # Send email to buyer
    buyer_subject = f"Purchase Confirmation - {bike_name}"
    buyer_body = f"""
    Dear {purchase.buyer_user.username},
    
    Your purchase of {bike_name} has been confirmed!
    
    Purchase Details:
    - Bike: {bike_name}
    - Price: ${purchase.price:.2f}
    - Purchase Date: {purchase.purchase_date.strftime('%Y-%m-%d %H:%M:%S')}
    - Seller: {purchase.seller_user.username}
    
    Thank you for using our platform!
    """
    
    # Send email to seller
    seller_subject = f"Bike Sold - {bike_name}"
    seller_body = f"""
    Dear {purchase.seller_user.username},
    
    Your bike {bike_name} has been sold!
    
    Sale Details:
    - Bike: {bike_name}
    - Price: ${purchase.price:.2f}
    - Sale Date: {purchase.purchase_date.strftime('%Y-%m-%d %H:%M:%S')}
    - Buyer: {purchase.buyer_user.username}
    
    Thank you for using our platform!
    """
    
    try:
        msg_buyer = Message(buyer_subject,
                          sender=app.config['MAIL_DEFAULT_SENDER'],
                          recipients=[buyer_email],
                          body=buyer_body)
        mail.send(msg_buyer)
        
        msg_seller = Message(seller_subject,
                           sender=app.config['MAIL_DEFAULT_SENDER'],
                           recipients=[seller_email],
                           body=seller_body)
        mail.send(msg_seller)
    except Exception as e:
        print(f"Error sending purchase confirmation emails: {str(e)}")

# Create database tables
def init_db():
    print("Initializing database...")
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database initialized successfully!")
    app.run(debug=True, port=5002)
