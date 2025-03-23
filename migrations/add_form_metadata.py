from flask import current_app
from alembic import op
import sqlalchemy as sa
from datetime import datetime

def upgrade():
    # Add new columns
    with current_app.app_context():
        op.add_column('bike', sa.Column('suggested_price', sa.Float(), nullable=True))
        op.add_column('bike', sa.Column('last_price_calculation', sa.DateTime(), nullable=True))
        op.add_column('bike', sa.Column('image_1_original_name', sa.String(200), nullable=True))
        op.add_column('bike', sa.Column('image_2_original_name', sa.String(200), nullable=True))
        op.add_column('bike', sa.Column('image_3_original_name', sa.String(200), nullable=True))
        op.add_column('bike', sa.Column('image_1_size', sa.Integer(), nullable=True))
        op.add_column('bike', sa.Column('image_2_size', sa.Integer(), nullable=True))
        op.add_column('bike', sa.Column('image_3_size', sa.Integer(), nullable=True))
        op.add_column('bike', sa.Column('form_submission_ip', sa.String(45), nullable=True))
        op.add_column('bike', sa.Column('form_submission_user_agent', sa.String(500), nullable=True))
        op.add_column('bike', sa.Column('last_updated_at', sa.DateTime(), nullable=True))

def downgrade():
    # Remove added columns
    with current_app.app_context():
        op.drop_column('bike', 'suggested_price')
        op.drop_column('bike', 'last_price_calculation')
        op.drop_column('bike', 'image_1_original_name')
        op.drop_column('bike', 'image_2_original_name')
        op.drop_column('bike', 'image_3_original_name')
        op.drop_column('bike', 'image_1_size')
        op.drop_column('bike', 'image_2_size')
        op.drop_column('bike', 'image_3_size')
        op.drop_column('bike', 'form_submission_ip')
        op.drop_column('bike', 'form_submission_user_agent')
        op.drop_column('bike', 'last_updated_at')