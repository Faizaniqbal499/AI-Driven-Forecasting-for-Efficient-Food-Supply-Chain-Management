"""
Configuration settings for Food Forecast AI application.
Uses environment variables for production readiness.
"""

import os
from datetime import timedelta

# Get the absolute path of the project root directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration class."""
    
    # ============================================
    # FLASK CORE SETTINGS
    # ============================================
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production-2026')
    
    # Debug mode - NEVER True in production
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # ============================================
    # DATABASE SETTINGS
    # ============================================
    # SQLite for development, PostgreSQL for production
    DATABASE_URL = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{os.path.join(BASE_DIR, "instance", "food_forecast.db")}'
    )
    
    # For SQLite compatibility with SQLAlchemy (if used later)
    if DATABASE_URL.startswith('sqlite:///'):
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ============================================
    # FILE UPLOAD SETTINGS
    # ============================================
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(BASE_DIR, 'uploads'))
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 100 * 1024 * 1024))  # 100MB default
    
    # Allowed file extensions for upload
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'json', 'pdf', 'pkl', 'txt'}
    
    # ============================================
    # SESSION SETTINGS
    # ============================================
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Session timeout - 50 minutes of inactivity
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=50)

    # Reset session timer on each request (user activity)
    SESSION_REFRESH_EACH_REQUEST = True
    
    # Remember me cookie duration (30 days)
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    REMEMBER_COOKIE_SECURE = os.environ.get('REMEMBER_COOKIE_SECURE', 'False').lower() == 'true'
    REMEMBER_COOKIE_HTTPONLY = True

    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.environ.get('CSRF_SECRET_KEY', SECRET_KEY)
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    
    # Rate limiting (optional, implement in app.py)
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = 'memory://'
    RATELIMIT_DEFAULT = '100 per day, 10 per minute'
    
    # ============================================
    # ML MODEL SETTINGS
    # ============================================
    # Path to store trained models
    MODELS_FOLDER = os.environ.get('MODELS_FOLDER', os.path.join(BASE_DIR, 'models'))
    
    # Available ML models configuration
    # ONLY includes models that are actually trained and implemented
    AVAILABLE_MODELS = {
        'linear': {
            'key': 'linear',
            'name': 'Linear Regression',
            'category': 'regression',
            'category_name': 'Regression - Statistical',
            'enabled': True,
            'icon': 'chart-line',
            'icon_class': 'regression',
            'complexity': 'Low Complexity',
            'complexity_class': 'low',
            'featured': False,
            'description': 'Predicts food demand based on linear relationships with day of week, weather conditions, and historical sales patterns.',
            'full_description': 'A fundamental statistical method for predicting continuous outcomes based on linear relationships between variables. Best for simple, linear demand patterns in restaurant forecasting.',
            'use_cases': [
                'Daily customer count prediction',
                'Basic menu item demand forecasting',
                'Quick initial forecasts',
                'Trend analysis and visualization'
            ],
            'recommended_for': 'Small restaurants with linear demand patterns, quick daily forecasting needs, and situations where interpretability is more important than maximum accuracy.',
            'accuracy': '89',
            'accuracy_label': 'R2 Score',
            'train_time': '1.2s',
            'predict_time': '0.05s',
            'size': '15KB',
            'bg_color': 'rgba(59, 130, 246, 0.1)',
            'color': '#3b82f6',
            'docs_url': '#',
            'default_params': {
                'fit_intercept': True,
                'normalize': False
            }
        },
        'arima': {
            'key': 'arima',
            'name': 'ARIMA',
            'category': 'time_series',
            'category_name': 'Time Series - Forecasting',
            'enabled': True,
            'icon': 'wave-square',
            'icon_class': 'time-series',
            'complexity': 'Medium Complexity',
            'complexity_class': 'medium',
            'featured': True,
            'description': 'Advanced time series model for seasonal food demand patterns, holidays, and recurring weekly/monthly trends.',
            'full_description': 'AutoRegressive Integrated Moving Average (ARIMA) - excels at capturing temporal dependencies and seasonal patterns in restaurant demand data.',
            'use_cases': [
                'Seasonal menu planning',
                'Holiday demand spike prediction',
                'Weekly restaurant traffic forecasting',
                'Event-based demand estimation'
            ],
            'recommended_for': 'Restaurants with strong seasonal patterns, established weekly cycles, and historical data spanning multiple months.',
            'accuracy': '92',
            'accuracy_label': 'Accuracy',
            'train_time': '3.8s',
            'predict_time': '0.12s',
            'size': '45KB',
            'bg_color': 'rgba(168, 85, 247, 0.1)',
            'color': '#8b5cf6',
            'docs_url': '#',
            'default_params': {
                'p': 5,
                'd': 1,
                'q': 0
            }
        },
        'lstm': {
            'key': 'lstm',
            'name': 'LSTM',
            'category': 'neural',
            'category_name': 'Neural Network - Deep Learning',
            'enabled': True,
            'icon': 'network-wired',
            'icon_class': 'neural',
            'complexity': 'High Complexity',
            'complexity_class': 'high',
            'featured': False,
            'description': 'Deep learning model that captures complex patterns in customer behavior, weather impacts, and special events.',
            'full_description': 'Long Short-Term Memory (LSTM) neural network - ideal for capturing long-term dependencies and complex non-linear patterns in demand data.',
            'use_cases': [
                'Multi-factor demand prediction',
                'Weather impact analysis',
                'Event-driven demand spikes',
                'Long-term trend forecasting'
            ],
            'recommended_for': 'Large restaurants with extensive historical data and complex demand patterns influenced by multiple factors.',
            'accuracy': '95',
            'accuracy_label': 'Accuracy',
            'train_time': '28.5s',
            'predict_time': '0.25s',
            'size': '12.3MB',
            'bg_color': 'rgba(249, 115, 22, 0.1)',
            'color': '#f97316',
            'docs_url': '#',
            'default_params': {
                'units': 50,
                'epochs': 100,
                'batch_size': 32
            }
        },
        'xgboost': {
            'key': 'xgboost',
            'name': 'XGBoost',
            'category': 'ensemble',
            'category_name': 'Ensemble - Tree-based',
            'enabled': True,
            'icon': 'layer-group',
            'icon_class': 'ensemble',
            'complexity': 'Medium Complexity',
            'complexity_class': 'medium',
            'featured': False,
            'description': 'Gradient boosting model that excels at capturing non-linear relationships between multiple demand factors.',
            'full_description': 'Extreme Gradient Boosting (XGBoost) - an ensemble method that combines multiple decision trees for robust predictions.',
            'use_cases': [
                'Age-group specific demand analysis',
                'Menu item combination optimization',
                'External factor integration',
                'High-accuracy demand predictions'
            ],
            'recommended_for': 'Restaurants wanting to understand which factors most influence demand, with good balance of accuracy and interpretability.',
            'accuracy': '96',
            'accuracy_label': 'Accuracy',
            'train_time': '4.7s',
            'predict_time': '0.08s',
            'size': '8.2MB',
            'bg_color': 'rgba(34, 197, 94, 0.1)',
            'color': '#10b981',
            'docs_url': '#',
            'default_params': {
                'n_estimators': 100,
                'max_depth': 6,
                'learning_rate': 0.1
            }
        },
        'gru': {
            'key': 'gru',
            'name': 'GRU',
            'category': 'neural',
            'category_name': 'Neural Network - Deep Learning',
            'enabled': True,
            'icon': 'microchip',
            'icon_class': 'neural',
            'complexity': 'High Complexity',
            'complexity_class': 'high',
            'featured': False,
            'description': 'Gated Recurrent Unit - efficient deep learning model for sequential demand forecasting with faster training than LSTM.',
            'full_description': 'Gated Recurrent Unit (GRU) - a simplified LSTM variant that performs similarly with fewer parameters and faster training times.',
            'use_cases': [
                'Sequential demand pattern analysis',
                'Real-time forecasting applications',
                'Resource-constrained deployments',
                'Similar accuracy to LSTM with less computation'
            ],
            'recommended_for': 'Restaurants wanting neural network performance with faster training times and lower computational requirements than LSTM.',
            'accuracy': '94',
            'accuracy_label': 'Accuracy',
            'train_time': '18.2s',
            'predict_time': '0.18s',
            'size': '6.8MB',
            'bg_color': 'rgba(236, 72, 153, 0.1)',
            'color': '#ec4899',
            'docs_url': '#',
            'default_params': {
                'units': 50,
                'epochs': 80,
                'batch_size': 32,
                'dropout': 0.2
            }
        }
    }
    
    # ============================================
    # EMAIL SETTINGS (for notifications)
    # ============================================
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@foodforecast.ai')
    
    # ============================================
    # LOGGING SETTINGS
    # ============================================
    LOG_FOLDER = os.environ.get('LOG_FOLDER', os.path.join(BASE_DIR, 'logs'))
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # ============================================
    # API SETTINGS (for external services)
    # ============================================
    # Weather API (e.g., OpenWeatherMap)
    WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY', '')
    WEATHER_API_URL = 'https://api.openweathermap.org/data/2.5/weather'
    
    # Google OAuth
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    
    # Microsoft OAuth
    MICROSOFT_CLIENT_ID = os.environ.get('MICROSOFT_CLIENT_ID', '')
    MICROSOFT_CLIENT_SECRET = os.environ.get('MICROSOFT_CLIENT_SECRET', '')
    MICROSOFT_TENANT_ID = os.environ.get('MICROSOFT_TENANT_ID', 'common')
    
    # ============================================
    # APPLICATION SETTINGS
    # ============================================
    APP_NAME = 'Food Forecast AI'
    APP_VERSION = '1.0.0'
    
    # Pagination defaults
    ITEMS_PER_PAGE = 10
    MAX_PAGE_RANGE = 5  # Number of page links to show in pagination
    
    # Dashboard settings
    FORECAST_DAYS = 7
    TOP_ITEMS_COUNT = 4
    MAX_ALERTS_DISPLAY = 5
    
    # ============================================
    # CACHE SETTINGS (optional)
    # ============================================
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'SimpleCache')
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    
    # ============================================
    # FEATURE FLAGS
    # ============================================
    FEATURES = {
        'social_login': os.environ.get('FEATURE_SOCIAL_LOGIN', 'False').lower() == 'true',
        'email_notifications': os.environ.get('FEATURE_EMAIL_NOTIFICATIONS', 'False').lower() == 'true',
        'advanced_ml_models': True,  # LSTM, GRU available
        'waste_tracking': True,
        'customer_demographics': True,
        'export_reports': True,
    }


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    DATABASE_URL = f'sqlite:///{os.path.join(BASE_DIR, "instance", "food_forecast_dev.db")}'
    RATELIMIT_ENABLED = False


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    DATABASE_URL = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    
    # SECRET_KEY with default fallback - no ValueError checks to allow app to run with default key (not recommended for production)
    SECRET_KEY = os.environ.get('SECRET_KEY', 'food-forecast-fyp-2025-secure-key')
    
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    
    # DATABASE_URL with default fallback
    DATABASE_URL = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.join(BASE_DIR, "instance", "food_forecast.db")}')
    
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')


# Configuration dictionary for easy switching
config_dict = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(env=None):
    """
    Get configuration class based on environment.
    
    Args:
        env (str): Environment name ('development', 'testing', 'production')
    
    Returns:
        Config class for the specified environment
    """
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    
    return config_dict.get(env, DevelopmentConfig)


# ============================================
# CREATE REQUIRED DIRECTORIES
# ============================================
def ensure_directories():
    """Create necessary directories if they don't exist."""
    directories = [
        Config.UPLOAD_FOLDER,
        Config.MODELS_FOLDER,
        Config.LOG_FOLDER,
        os.path.join(BASE_DIR, 'instance'),
    ]
    
    for directory in directories:
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")


# Auto-create directories when config is imported
try:
    ensure_directories()
except Exception as e:
    print(f"Warning: Could not create directories - {e}")