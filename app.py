"""
app.py - Application Factory
Entry point for the Acadify Flask application.
Uses the Application Factory pattern for modularity and testing.
"""

from flask import Flask, render_template
from config import config
from extensions import db, migrate, login_manager


def create_app(config_name='development'):
    """
    Application Factory Function
    
    Args:
        config_name (str): Configuration to use ('development', 'production', 'testing')
    
    Returns:
        Flask: Configured Flask application instance
    """
    # Initialize Flask app
    app = Flask(__name__)
    
    # Load configuration from config.py based on environment
    app.config.from_object(config[config_name])
    
    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # Configure Flask-Login
    login_manager.login_view = 'auth.login'  # Redirect to login page if not authenticated
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # User loader callback for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for Flask-Login session management"""
        from models import User
        return User.query.get(int(user_id))
    
    # Register blueprints (routes)
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Import models so Flask-Migrate can detect them
    with app.app_context():
        # Import all models here
        import models
    
    return app


def register_blueprints(app):
    """
    Register all application blueprints (modular route handlers)
    """
    # Import blueprints
    from blueprints.auth.routes import auth_bp
    from blueprints.student.routes import student_bp
    from blueprints.teacher.routes import teacher_bp
    from blueprints.ocr.routes import ocr_bp
    
    # Register with URL prefixes
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(teacher_bp, url_prefix='/teacher')
    app.register_blueprint(ocr_bp, url_prefix='/ocr')
    
    # Register home/landing page route
    @app.route('/')
    def index():
        """Landing page"""
        return render_template('index.html')


def register_error_handlers(app):
    """
    Register custom error handlers for common HTTP errors
    """
    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()  # Rollback any failed database transactions
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html'), 403


# Run the application
if __name__ == '__main__':
    # Create app instance (always use development config)
    app = create_app('development')
    
    # Run the development server
    app.run(
        host='0.0.0.0',  # Allow external connections
        port=5000,
        debug=True  # Always debug mode during development
    )