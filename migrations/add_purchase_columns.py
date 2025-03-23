from flask import current_app
from flask_migrate import Migrate
from datetime import datetime

def upgrade():
    """Add missing columns to purchase table"""
    with current_app.app_context():
        db = current_app.extensions['sqlalchemy'].db
        
        # Add missing columns one by one to avoid potential issues
        db.engine.execute('''
            ALTER TABLE purchase ADD COLUMN payment_status VARCHAR(20) DEFAULT 'pending';
            ALTER TABLE purchase ADD COLUMN payment_method VARCHAR(50);
            ALTER TABLE purchase ADD COLUMN payment_reference VARCHAR(100);
            ALTER TABLE purchase ADD COLUMN payment_date DATETIME;
            ALTER TABLE purchase ADD COLUMN seller_notes TEXT;
            ALTER TABLE purchase ADD COLUMN rejection_reason TEXT;
            ALTER TABLE purchase ADD COLUMN bill_of_sale VARCHAR(200);
            ALTER TABLE purchase ADD COLUMN registration_transfer VARCHAR(200);
            ALTER TABLE purchase ADD COLUMN inspection_report VARCHAR(200);
            ALTER TABLE purchase ADD COLUMN delivery_status VARCHAR(20);
            ALTER TABLE purchase ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP;
            ALTER TABLE purchase ADD COLUMN completed_at DATETIME;
            ALTER TABLE purchase ADD COLUMN cancelled_at DATETIME;
            ALTER TABLE purchase ADD COLUMN ip_address VARCHAR(45);
            ALTER TABLE purchase ADD COLUMN user_agent VARCHAR(500);
            ALTER TABLE purchase ADD COLUMN platform VARCHAR(50);
        ''')

def downgrade():
    """Remove added columns from purchase table"""
    with current_app.app_context():
        db = current_app.extensions['sqlalchemy'].db
        
        # Remove columns in reverse order
        columns_to_drop = [
            'platform', 'user_agent', 'ip_address', 'cancelled_at', 'completed_at',
            'updated_at', 'delivery_status', 'inspection_report', 'registration_transfer',
            'bill_of_sale', 'rejection_reason', 'seller_notes', 'payment_date',
            'payment_reference', 'payment_method', 'payment_status'
        ]
        
        for column in columns_to_drop:
            db.engine.execute(f'ALTER TABLE purchase DROP COLUMN {column};')