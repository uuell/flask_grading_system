"""
blueprints/auth/routes.py - Authentication Blueprint
Handles user login, logout, registration, and password management.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

# Create blueprint
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login page
    GET: Display login form
    POST: Process login credentials
    """
    # If already logged in, redirect to appropriate dashboard
    if current_user.is_authenticated:
        if current_user.role == 'teacher':
            return redirect(url_for('teacher.dashboard'))
        else:
            return redirect(url_for('student.dashboard'))
    
    # TODO: Implement login logic
    return "Login Page - Coming Soon"


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Registration page
    GET: Display registration form
    POST: Create new user account
    """
    # TODO: Implement registration logic
    return "Register Page - Coming Soon"


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
    """
    # TODO: Implement password reset logic
    return "Forgot Password - Coming Soon"