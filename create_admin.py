"""
create_admin.py - Quick script to create an admin account
Run this from your project root directory: python create_admin.py
"""

from app import create_app
from models import User
from extensions import db, bcrypt

# Create app instance
app = create_app('development')

with app.app_context():
    # Check if admin already exists
    existing_admin = User.query.filter_by(email='admin@acadify.edu').first()
    
    if existing_admin:
        print("❌ Admin account already exists!")
        print(f"   Email: {existing_admin.email}")
        print(f"   Role: {existing_admin.role}")
    else:
        # Create admin user
        admin = User(
            email='admin@acadify.edu',
            password=bcrypt.generate_password_hash('admin123').decode('utf-8'),
            role='admin'
        )
        
        db.session.add(admin)
        db.session.commit()
        
        print("✅ Admin account created successfully!")
        print("-" * 50)
        print("Login credentials:")
        print("  Email: admin@acadify.edu")
        print("  Password: admin123")
        print("-" * 50)
        print("⚠️ IMPORTANT: Change this password after first login!")
    
    # Show all users
    all_users = User.query.all()
    print(f"\n📊 Total users in database: {len(all_users)}")
    
    if all_users:
        print("\nAll users:")
        for user in all_users:
            print(f"  • {user.email} ({user.role})")