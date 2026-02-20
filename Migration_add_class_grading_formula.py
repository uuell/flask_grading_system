"""
Database Migration: Add Grading Formula to Class Model
Adds fields for manual subject input and per-class grading formulas

Run this migration after updating models.py:
    flask db migrate -m "Add grading formula to Class"
    flask db upgrade

Changes:
- Add subject_name (String, nullable) - Manual subject name input
- Add subject_code (String, nullable) - Manual subject code (e.g., "CS201")
- Add units (Integer, nullable) - Manual units input
- Add grading_formula (Text, nullable) - JSON formula per class
- Add grade_conversion_table (Text, nullable) - Custom conversion (optional)
- Make subject_id nullable (backward compatibility)
"""

from alembic import op
import sqlalchemy as sa


def upgrade():
    """Apply changes to add grading formula fields"""
    
    # Add new fields to class table
    op.add_column('class', sa.Column('subject_name', sa.String(200), nullable=True))
    op.add_column('class', sa.Column('subject_code', sa.String(20), nullable=True))
    op.add_column('class', sa.Column('units', sa.Integer, nullable=True))
    op.add_column('class', sa.Column('grading_formula', sa.Text, nullable=True))
    op.add_column('class', sa.Column('grade_conversion_table', sa.Text, nullable=True))
    
    # Make subject_id nullable (for backward compatibility)
    # Note: This assumes you're using PostgreSQL or MySQL
    # For SQLite, you may need to recreate the table
    with op.batch_alter_table('class') as batch_op:
        batch_op.alter_column('subject_id',
                              existing_type=sa.Integer(),
                              nullable=True)


def downgrade():
    """Revert changes"""
    
    # Remove added columns
    op.drop_column('class', 'grade_conversion_table')
    op.drop_column('class', 'grading_formula')
    op.drop_column('class', 'units')
    op.drop_column('class', 'subject_code')
    op.drop_column('class', 'subject_name')
    
    # Make subject_id non-nullable again
    with op.batch_alter_table('class') as batch_op:
        batch_op.alter_column('subject_id',
                              existing_type=sa.Integer(),
                              nullable=False)


# Manual SQL commands (if not using Flask-Migrate/Alembic):
"""
-- For manual migration, run these SQL commands:

ALTER TABLE class ADD COLUMN subject_name VARCHAR(200);
ALTER TABLE class ADD COLUMN subject_code VARCHAR(20);
ALTER TABLE class ADD COLUMN units INTEGER;
ALTER TABLE class ADD COLUMN grading_formula TEXT;
ALTER TABLE class ADD COLUMN grade_conversion_table TEXT;

-- Make subject_id nullable (syntax varies by database)
-- PostgreSQL:
ALTER TABLE class ALTER COLUMN subject_id DROP NOT NULL;

-- MySQL:
ALTER TABLE class MODIFY subject_id INT NULL;

-- SQLite (requires table recreation):
-- Create backup, drop, recreate with new schema, restore data
"""