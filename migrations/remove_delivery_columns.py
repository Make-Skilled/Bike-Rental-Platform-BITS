from flask import current_app
from flask_migrate import Migrate

def upgrade():
    """Remove delivery-related columns from purchase table"""
    with current_app.app_context():
        db = current_app.extensions['sqlalchemy'].db
        
        # Remove columns
        columns_to_drop = ['delivery_method', 'delivery_address', 'delivery_date']
        for column in columns_to_drop:
            db.engine.execute(f'ALTER TABLE purchase DROP COLUMN IF EXISTS {column};')

def downgrade():
    """Add back delivery-related columns to purchase table"""
    with current_app.app_context():
        db = current_app.extensions['sqlalchemy'].db
        
        # Add delivery-related columns back
        db.engine.execute('''
            ALTER TABLE purchase ADD COLUMN IF NOT EXISTS delivery_method VARCHAR(50);
            ALTER TABLE purchase ADD COLUMN IF NOT EXISTS delivery_address TEXT;
            ALTER TABLE purchase ADD COLUMN IF NOT EXISTS delivery_date DATETIME;
        ''')