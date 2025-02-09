import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Minimal settings needed for ORM only
SECRET_KEY = 'your-secret-key-here'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-west-1")

# Application definition
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'app.models.apps.ModelsConfig',  # Use the app config instead of 'app.models'
]

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'your_db_name'),
        'USER': os.getenv('POSTGRES_USER', 'your_db_user'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'your_db_password'),
        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}

REDIS_HOST: str = os.getenv("REDIS_HOST")
REDIS_PORT: str = os.getenv("REDIS_PORT")

CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/0",
        }
    }

# Required for Django ORM
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_TZ = True

# API Keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# Add this setting
AUTH_USER_MODEL = 'auth.User'

ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY")
SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY")

EMAIL_BACKEND = "django_ses.SESBackend"
