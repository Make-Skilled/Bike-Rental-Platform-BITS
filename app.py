from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
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
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///bikerental.db')
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
migrate = Migrate(app, db)

# Add configurations for image uploads
UPLOAD_FOLDER = 'static/bike_images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Add timestamp to filename to make it unique
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        
        # Create upload folder if it doesn't exist
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
            
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        return os.path.join('bike_images', filename)  # Return relative path
    return None

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile = db.Column(db.String(15), nullable=True)  # Adding mobile number field
    password = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bikes = db.relationship('Bike', backref='owner', lazy=True)
    rentals = db.relationship('Rental', backref='renter', lazy=True, foreign_keys='Rental.renter_id')
    rental_requests = db.relationship('RentalRequest', backref='requester', lazy=True, foreign_keys='RentalRequest.requester_id')

# Bike Model
class Bike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    condition = db.Column(db.String(50), nullable=False)
    price_per_day = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    image_url_1 = db.Column(db.String(500))
    image_url_2 = db.Column(db.String(500))
    image_url_3 = db.Column(db.String(500))
    rentals = db.relationship('Rental', backref='bike', lazy=True)
    rental_requests = db.relationship('RentalRequest', backref='bike', lazy=True)

# Rental Model
class Rental(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bike_id = db.Column(db.Integer, db.ForeignKey('bike.id'), nullable=False)
    renter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, active, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Rental Request Model
class RentalRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bike_id = db.Column(db.Integer, db.ForeignKey('bike.id'), nullable=False)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
        new_user = User(username=username, email=email, mobile=mobile, password=hashed_password)
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
        
        if user and check_password_hash(user.password, password):
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
            # Get form data
            name = request.form.get('name')
            model = request.form.get('model')
            year = request.form.get('year')
            condition = request.form.get('condition')
            price_per_day = request.form.get('price_per_day')
            description = request.form.get('description')

            # Handle image uploads
            image_url_1 = None
            image_url_2 = None
            image_url_3 = None

            if 'image1' in request.files:
                image_url_1 = save_image(request.files['image1'])
            if 'image2' in request.files:
                image_url_2 = save_image(request.files['image2'])
            if 'image3' in request.files:
                image_url_3 = save_image(request.files['image3'])

            if not image_url_1:
                flash('Please upload at least one image', 'danger')
                return redirect(url_for('add_bike'))

            # Create new bike
            bike = Bike(
                name=name,
                model=model,
                year=year,
                condition=condition,
                price_per_day=price_per_day,
                description=description,
                owner_id=session['user_id'],
                image_url_1=image_url_1,
                image_url_2=image_url_2,
                image_url_3=image_url_3
            )

            try:
                db.session.add(bike)
                db.session.commit()
                flash('Bike added successfully!', 'success')
                return redirect(url_for('my_bikes'))
            except Exception as e:
                db.session.rollback()
                flash('Error adding bike. Please try again.', 'danger')
                return redirect(url_for('add_bike'))

        except Exception as e:
            db.session.rollback()
            flash('Error adding bike. Please try again.')
            return render_template('add_bike.html')
    
    return render_template('add_bike.html')

@app.route('/bikes/my-bikes')
@login_required
def my_bikes():
    user_bikes = Bike.query.filter_by(owner_id=session['user_id']).all()
    return render_template('my_bikes.html', bikes=user_bikes)

@app.route('/bikes/<int:bike_id>')
def view_bike(bike_id):
    bike = Bike.query.get_or_404(bike_id)
    return render_template('view_bike.html', bike=bike)

@app.route('/bikes/<int:bike_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_bike(bike_id):
    bike = Bike.query.get_or_404(bike_id)
    if bike.owner_id != session['user_id']:
        flash('You can only edit your own bikes')
        return redirect(url_for('my_bikes'))
    
    if request.method == 'POST':
        try:
            bike.name = request.form['name']
            bike.model = request.form['model']
            bike.year = int(request.form['year'])
            bike.condition = request.form['condition']
            bike.price_per_day = float(request.form['price_per_day'])
            bike.description = request.form['description']
            bike.is_available = 'is_available' in request.form
            
            db.session.commit()
            flash('Bike updated successfully!')
            return redirect(url_for('my_bikes'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating bike. Please try again.')
    
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
            requester_id=session['user_id'],
            start_date=start_date,
            end_date=end_date,
            message=message,
            status='pending'
        )
        
        db.session.add(rental_request)
        db.session.commit()
        print(f"Rental request {rental_request.id} created successfully")
        
        owner = User.query.get(bike.owner_id)
        if owner.email:
            send_notification_email(
                'New Rental Request',
                owner.email,
                'email/new_request.html',
                user=User.query.get(session['user_id']),
                bike=bike,
                request=rental_request
            )
        
        flash('Your rental request has been sent! The owner will review it and respond soon.')
        return redirect(url_for('my_rental_requests'))
        
    return render_template('request_rental.html', bike=bike, today=datetime.now().strftime('%Y-%m-%d'))

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
    
    sent_requests = RentalRequest.query.filter_by(requester_id=user_id).order_by(RentalRequest.created_at.desc()).all()
    
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
        
    requester = User.query.get(rental_request.requester_id)
    
    if action == 'approve':
        # Calculate rental duration and total price
        rental_days = (rental_request.end_date - rental_request.start_date).days
        total_price = rental_days * bike.price_per_day
        
        # Create a new rental with status 'active'
        rental = Rental(
            bike_id=bike.id,
            renter_id=rental_request.requester_id,
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
    app.run(debug=True)
