"""
config.py - Configuration Classes
Manages different configurations for development, production, and testing environments.
"""

import os
from datetime import timedelta


class Config:
    """
    Base Configuration Class
    Contains settings shared across all environments.
    """
    # Secret key for session management and CSRF protection
    # In production, load from environment variable
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Disable modification tracking (saves resources)
    
    # File upload configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'csv', 'xlsx', 'xls'}
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)  # Session expires after 7 days
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookie
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
    
    # Pagination
    ITEMS_PER_PAGE = 50
    STUDENTS_PER_PAGE = 50
    CLASSES_PER_PAGE = 20
    
    # ========================================
    # HYBRID ACADEMIC YEAR SETTINGS
    # Priority: Database > Auto-Calculate
    # ========================================
    
    @staticmethod
    def _auto_calculate_school_year():
        """
        Auto-calculate school year based on current date
        
        Logic:
        - August to December → YYYY-YYYY+1
        - January to July → YYYY-1-YYYY
        
        Examples:
        - August 2025 → "2025-2026"
        - January 2026 → "2025-2026"
        """
        from datetime import datetime
        now = datetime.now()
        year = now.year
        month = now.month
        
        if month >= 8:  # August onwards = new school year
            return f"{year}-{year + 1}"
        else:  # January to July = previous school year
            return f"{year - 1}-{year}"
    
    @staticmethod
    def _auto_calculate_semester():
        """
        Auto-calculate semester based on current date
        
        Logic:
        - August to December → 1st Semester
        - January to May → 2nd Semester
        - June to July → Summer
        """
        from datetime import datetime
        month = datetime.now().month
        
        if 8 <= month <= 12:
            return "1st Semester"
        elif 1 <= month <= 5:
            return "2nd Semester"
        else:  # June-July
            return "Summer"
    
    @staticmethod
    def get_current_school_year():
        """
        Get current school year
        Priority: Database setting > Auto-calculate
        """
        try:
            from models import SystemSettings
            db_value = SystemSettings.get_setting('current_school_year')
            if db_value:
                return db_value
        except:
            # Database not available yet (during initial setup/migration)
            pass
        
        # Fallback to auto-calculation
        return Config._auto_calculate_school_year()
    
    @staticmethod
    def get_current_semester():
        """
        Get current semester
        Priority: Database setting > Auto-calculate
        """
        try:
            from models import SystemSettings
            db_value = SystemSettings.get_setting('current_semester')
            if db_value:
                return db_value
        except:
            # Database not available yet
            pass
        
        # Fallback to auto-calculation
        return Config._auto_calculate_semester()
    
    # ✅ Use the hybrid methods
    CURRENT_SCHOOL_YEAR = property(lambda self: Config.get_current_school_year())
    CURRENT_SEMESTER = property(lambda self: Config.get_current_semester())
    
    # Grade Settings (Philippine System)
    PASSING_GRADE = 3.0  # 3.0 and below is passing
    FAILED_GRADE = 5.0   # 5.0 is failed
    INCOMPLETE_GRADE = 'INC'
    DROPPED_GRADE = 'DRP'
    
    # Default Grade Conversion (Percentage to PH Grade)
    DEFAULT_GRADE_CONVERSION = {
        "97-100": 1.0,
        "94-96": 1.25,
        "91-93": 1.5,
        "88-90": 1.75,
        "85-87": 2.0,
        "82-84": 2.25,
        "79-81": 2.5,
        "76-78": 2.75,
        "75": 3.0,
        "65-74": 4.0,
        "0-64": 5.0
    }
    
    # CSV Upload Settings
    CSV_ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
    CSV_MAX_ROWS = 10000  # Maximum rows per CSV upload
    
    # Email Configuration (for sending credentials)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@acadify.edu')
    
    @classmethod
    def init_app(cls, app):
        """
        Initialize application with this config (optional hook)
        """
        pass


class DevelopmentConfig(Config):
    """
    Development Configuration
    Used for local development with debug mode enabled.
    """
    DEBUG = True
    TESTING = False
    
    # Use SQLite for development (easy setup, no separate database server needed)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), 'acadify_dev.db')
    
    # Development-specific settings
    SQLALCHEMY_ECHO = True  # Log all SQL queries (useful for debugging)
    
    # Less strict session settings for development
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """
    Production Configuration
    Used for deployed application with security hardened.
    """
    DEBUG = False
    TESTING = False
    
    # Use PostgreSQL or MySQL in production
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://username:password@localhost/acadify_prod'
    
    # Security settings
    SESSION_COOKIE_SECURE = True  # Require HTTPS for cookies
    
    # Performance optimizations
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_POOL_RECYCLE = 3600  # Recycle connections after 1 hour
    SQLALCHEMY_POOL_PRE_PING = True  # Verify connections before using
    
    # Disable SQL query logging in production
    SQLALCHEMY_ECHO = False
    
    @classmethod
    def init_app(cls, app):
        """
        Validate production settings when app is created
        """
        Config.init_app(app)
        
        # Ensure secret key is set in production
        if not os.environ.get('SECRET_KEY'):
            raise ValueError("SECRET_KEY environment variable must be set in production!")


class TestingConfig(Config):
    """
    Testing Configuration
    Used for running automated tests with isolated database.
    """
    DEBUG = False
    TESTING = True
    
    # Use in-memory SQLite for fast tests
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable CSRF protection in tests
    WTF_CSRF_ENABLED = False
    
    # Faster password hashing for tests
    BCRYPT_LOG_ROUNDS = 4
    
    # Disable SQL query logging in tests
    SQLALCHEMY_ECHO = False


# Configuration dictionary for easy access
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}