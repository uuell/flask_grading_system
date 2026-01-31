"""
blueprints/auth/routes.py - Authentication Blueprint
Handles user login, logout, and password management.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, bcrypt
from models import User, Student, Teacher

# Create blueprint
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/student-login', methods=['GET', 'POST'])
def student_login():
    """
    Student login page
    Uses student number instead of email
    """
    # If already logged in, redirect to dashboard
    if current_user.is_authenticated:
        if current_user.role == 'student':
            return redirect(url_for('student.dashboard'))
        else:
            flash('You are logged in as staff. Please logout first.', 'info')
            return redirect(url_for('index'))
    
    if request.method == 'POST':
        student_number = request.form.get('student_number', '').strip()
        password = request.form.get('password', '')
        
        # Validate input
        if not student_number or not password:
            flash('Please enter both Student ID and password.', 'danger')
            return render_template('auth/student_login.html')
        
        # Find student by student number
        student = Student.query.filter_by(student_number=student_number).first()
        
        if student is None:
            flash('Invalid Student ID or password.', 'danger')
            return render_template('auth/student_login.html')
        
        # Get the user account
        user = student.user
        
        # Check if user is actually a student
        if user.role != 'student':
            flash('This login is for students only.', 'danger')
            return render_template('auth/student_login.html')
        
        # Verify password
        if not bcrypt.check_password_hash(user.password, password):
            flash('Invalid Student ID or password.', 'danger')
            return render_template('auth/student_login.html')
        
        # Login successful
        login_user(user, remember=True)
        flash(f'Welcome back, {student.first_name}!', 'success')
        
        # Redirect to requested page or dashboard
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('student.dashboard'))
    
    # GET request - show login form
    return render_template('auth/student_login.html')


@auth_bp.route('/teacher-login', methods=['GET', 'POST'])
@auth_bp.route('/admin-login', methods=['GET', 'POST'])
def teacher_admin_login():
    """
    Teacher and Admin login page
    Uses email for authentication
    """
    # If already logged in, redirect to dashboard
    if current_user.is_authenticated:
        if current_user.role == 'teacher':
            return redirect(url_for('teacher.dashboard'))
        elif current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        else:
            flash('You are logged in as a student. Please logout first.', 'info')
            return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        # Validate input
        if not email or not password:
            flash('Please enter both email and password.', 'danger')
            return render_template('auth/teacher_admin_login.html')
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        if user is None:
            flash('Invalid email or password.', 'danger')
            return render_template('auth/teacher_admin_login.html')
        
        # Check if user is staff (teacher or admin)
        if user.role not in ['teacher', 'admin']:
            flash('This login is for faculty and staff only.', 'danger')
            return render_template('auth/teacher_admin_login.html')
        
        # Verify password
        if not bcrypt.check_password_hash(user.password, password):
            flash('Invalid email or password.', 'danger')
            return render_template('auth/teacher_admin_login.html')
        
        # Login successful
        login_user(user, remember=True)
        
        # Get name for welcome message
        if user.role == 'teacher':
            teacher = user.teacher_profile
            name = teacher.first_name if teacher else 'Teacher'
            flash(f'Welcome back, {name}!', 'success')
            return redirect(url_for('teacher.dashboard'))
        else:  # admin
            flash('Welcome back, Admin!', 'success')
            # For now, redirect to teacher dashboard (we'll create admin dashboard later)
            return redirect(url_for('teacher.dashboard'))
    
    # GET request - show login form
    return render_template('auth/teacher_admin_login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """
    Logout current user
    """
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """
    Password reset request page
    TODO: Implement password reset functionality
    """
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        flash('Password reset functionality coming soon. Please contact your administrator.', 'info')
        return redirect(url_for('auth.student_login'))
    
    return render_template('auth/forgot_password.html')


# Helper function to create test users (for development only)
@auth_bp.route('/create-test-users')
def create_test_users():
    """
    DEVELOPMENT ONLY: Create test users for testing
    Remove this in production!
    """
    try:
        # Check if users already exist
        if User.query.filter_by(email='admin@acadify.edu').first():
            return "Test users already exist!"
        
        # Create Admin User
        admin_user = User(
            email='admin@acadify.edu',
            password=bcrypt.generate_password_hash('admin123').decode('utf-8'),
            role='admin'
        )
        db.session.add(admin_user)
        
        # Create Teacher User
        teacher_user = User(
            email='teacher@acadify.edu',
            password=bcrypt.generate_password_hash('teacher123').decode('utf-8'),
            role='teacher'
        )
        db.session.add(teacher_user)
        db.session.flush()  # Get teacher_user.id
        
        # Create Teacher Profile
        teacher_profile = Teacher(
            user_id=teacher_user.id,
            employee_number='EMP-2024-001',
            first_name='Maria',
            last_name='Santos',
            department='College of Engineering',
            specialization='Computer Science'
        )
        db.session.add(teacher_profile)
        
        # Create Student User
        student_user = User(
            email='student@acadify.edu',
            password=bcrypt.generate_password_hash('student123').decode('utf-8'),
            role='student'
        )
        db.session.add(student_user)
        db.session.flush()  # Get student_user.id
        
        # Create Student Profile
        student_profile = Student(
            user_id=student_user.id,
            student_number='2024-00001',
            first_name='Juan',
            last_name='Dela Cruz',
            department='College of Engineering',
            program='BS Computer Science',
            year_level='1st Year',
            section='A'
        )
        db.session.add(student_profile)
        
        db.session.commit()
        
        return """
        <h1>Test Users Created Successfully!</h1>
        <h2>Login Credentials:</h2>
        <h3>Admin:</h3>
        <p>Email: admin@acadify.edu<br>Password: admin123</p>
        
        <h3>Teacher:</h3>
        <p>Email: teacher@acadify.edu<br>Password: teacher123</p>
        
        <h3>Student:</h3>
        <p>Student Number: 2024-00001<br>Password: student123</p>
        
        <br>
        <a href="/auth/student-login">Student Login</a> | 
        <a href="/auth/teacher-login">Teacher/Admin Login</a>
        
        <br><br>
        <strong>⚠️ IMPORTANT: Remove this route in production!</strong>
        """
        
    except Exception as e:
        db.session.rollback()
        return f"Error creating test users: {str(e)}"