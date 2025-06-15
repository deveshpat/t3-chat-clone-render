"""
Production settings for T3 Chat Clone on PythonAnywhere
"""

from .settings import *
import os

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Update this with your PythonAnywhere domain
ALLOWED_HOSTS = [
    't3clone.pythonanywhere.com',
    'localhost',
    '127.0.0.1',
]

# Database for production (SQLite is fine for demo)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db_production.sqlite3',
    }
}

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Security settings for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# CORS settings for API access
CORS_ALLOWED_ORIGINS = [
    "https://t3clone.pythonanywhere.com",
]

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django_production.log'),
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'chat': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Cache configuration (using dummy cache for simplicity)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Disable channels for production (WebSocket not supported on free PythonAnywhere)
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'channels']

# Use default ASGI application
ASGI_APPLICATION = None

# Remove channels middleware
MIDDLEWARE = [mw for mw in MIDDLEWARE if 'channels.middleware' not in mw] 