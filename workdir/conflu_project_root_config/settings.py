import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url
from datetime import timedelta
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT_DIR = BASE_DIR.parent

dotenv_path = PROJECT_ROOT_DIR / '.env'
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    pass

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-defaultfallbacksecretkeyforcheck')
DEBUG_STR = os.getenv('DJANGO_DEBUG', 'True')
DEBUG = DEBUG_STR.lower() in ('true', '1', 't')

ALLOWED_HOSTS_ENV = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_ENV.split(',') if host.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    'allauth',
    'allauth.account',
    # 'allauth.socialaccount',

    'rest_framework',
    'rest_framework.authtoken', # Required by dj-rest-auth if not using JWT for it
    'dj_rest_auth',
    'dj_rest_auth.registration', # Enables /registration/ endpoint via allauth

    'rest_framework_simplejwt',
    'guardian',
    'drf_spectacular',
    'drf_spectacular_sidecar',
    'storages',

    'core.apps.CoreConfig',
    'users.apps.UsersConfig',
    'workspaces.apps.WorkspacesConfig',
    'pages.apps.PagesConfig',
    'attachments.apps.AttachmentsConfig',
    'importer.apps.ImporterConfig',
    'llm_integrations.apps.LlmIntegrationsConfig',
    'api.apps.ApiConfig',
    'user_notifications.apps.UserNotificationsConfig',
    # 'django_celery_beat',
]

SITE_ID = 1

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
    'guardian.backends.ObjectPermissionBackend',
)

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]
ROOT_URLCONF = 'conflu_project_root_config.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [], 'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'conflu_project_root_config.wsgi.application'

DATABASES = {'default': dj_database_url.config(default=os.getenv('DATABASE_URL', f"sqlite:///{PROJECT_ROOT_DIR / 'db_dev_fallback.sqlite3'}"), conn_max_age=600)}
CACHES = {'default': {'BACKEND': 'django_redis.cache.RedisCache', 'LOCATION': os.getenv('REDIS_URL', 'redis://localhost:6379/0'), 'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'}}}

AUTH_PASSWORD_VALIDATORS = [{'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},{'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE = 'en-us'; TIME_ZONE = 'UTC'; USE_I18N = True; USE_TZ = True
STATIC_URL = 'static/'; DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        # SessionAuthentication is useful for browsing the API with Django admin login
        'rest_framework.authentication.SessionAuthentication',
        # dj_rest_auth can also use TokenAuthentication if preferred over JWT for some endpoints
        # 'dj_rest_auth.jwt_auth.JWTCookieAuthentication', # If using JWT cookies
    ),
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticatedOrReadOnly'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}
SIMPLE_JWT = {'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15), 'REFRESH_TOKEN_LIFETIME': timedelta(days=7),'ROTATE_REFRESH_TOKENS': True, 'BLACKLIST_AFTER_ROTATION': False, 'UPDATE_LAST_LOGIN': True, 'ALGORITHM': 'HS256','AUTH_HEADER_TYPES': ('Bearer',), 'USER_ID_FIELD': 'id', 'USER_ID_CLAIM': 'user_id'}

# dj-rest-auth specific settings
REST_AUTH = {
    'USE_JWT': True, # Tell dj-rest-auth to use Simple JWT
    'JWT_AUTH_HTTPONLY': False, # False so JavaScript can access tokens from cookies if using cookie auth
    # 'USER_DETAILS_SERIALIZER': 'path.to.your.UserDetailsSerializer', # Optional
    # 'REGISTER_SERIALIZER': 'path.to.your.RegisterSerializer', # Optional, if customizing registration
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Conflu Clone API', 'DESCRIPTION': 'API documentation for the Conflu Clone project.',
    'VERSION': '0.1.0', 'SERVE_INCLUDE_SCHEMA': True,
    'SWAGGER_UI_DIST': 'SIDECAR', 'SWAGGER_UI_FAVICON_HREF': 'SIDECAR', 'REDOC_DIST': 'SIDECAR',
}

SENTRY_DSN = os.getenv('CC_SENTRY_DSN')
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN, integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=float(os.getenv('CC_SENTRY_TRACES_SAMPLE_RATE', '0.1')),
        send_default_pii=False, environment=os.getenv('CC_ENVIRONMENT_NAME', 'development'),
        release=os.getenv('APP_RELEASE_VERSION', 'conflu@0.1.0-dev')
    )
else:
    pass

CC_STORAGE_BACKEND = os.getenv('CC_STORAGE_BACKEND', 'local').lower()
MEDIA_URL = '/media/'
if CC_STORAGE_BACKEND == 's3':
    AWS_ACCESS_KEY_ID = os.getenv('CC_AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('CC_AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('CC_AWS_STORAGE_BUCKET_NAME')
    AWS_S3_ENDPOINT_URL = os.getenv('CC_AWS_S3_ENDPOINT_URL')
    AWS_S3_REGION_NAME = os.getenv('CC_AWS_S3_REGION_NAME')
    AWS_S3_USE_SSL = os.getenv('CC_AWS_S3_USE_SSL', 'True').lower() == 'true'
    AWS_S3_VERIFY = os.getenv('CC_AWS_S3_VERIFY', 'True').lower() == 'true'
    AWS_S3_FILE_OVERWRITE = False; AWS_DEFAULT_ACL = None
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_STORAGE_BUCKET_NAME:
        DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    else:
        DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
        MEDIA_ROOT = PROJECT_ROOT_DIR / 'mediafiles_data_fallback'
        os.makedirs(MEDIA_ROOT, exist_ok=True)
else:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_ROOT = PROJECT_ROOT_DIR / 'mediafiles_data'
    os.makedirs(MEDIA_ROOT, exist_ok=True)

# Celery Configuration
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://redis:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_SEND_SENT_EVENT = True
# CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Test specific settings
if 'test' in sys.argv or 'pytest' in sys.argv:
    print("DEBUG: Applying test-specific Celery settings: CELERY_TASK_ALWAYS_EAGER=True")
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

# Django Allauth Specific Settings (can be customized further later)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
ACCOUNT_AUTHENTICATION_METHOD = os.getenv('ACCOUNT_AUTHENTICATION_METHOD', 'username_email')
ACCOUNT_EMAIL_REQUIRED = os.getenv('ACCOUNT_EMAIL_REQUIRED', 'True').lower() == 'true'
ACCOUNT_EMAIL_VERIFICATION = os.getenv('ACCOUNT_EMAIL_VERIFICATION', 'optional')
ACCOUNT_CONFIRM_EMAIL_ON_GET = os.getenv('ACCOUNT_CONFIRM_EMAIL_ON_GET', 'True').lower() == 'true'
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = os.getenv('ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION', 'True').lower() == 'true'
ACCOUNT_LOGOUT_ON_GET = os.getenv('ACCOUNT_LOGOUT_ON_GET', 'False').lower() == 'true'
ACCOUNT_LOGIN_ATTEMPTS_LIMIT = int(os.getenv('ACCOUNT_LOGIN_ATTEMPTS_LIMIT', '5'))
ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT = int(os.getenv('ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT', '300'))
LOGIN_REDIRECT_URL = os.getenv('LOGIN_REDIRECT_URL', "/")
ACCOUNT_LOGOUT_REDIRECT_URL = os.getenv('ACCOUNT_LOGOUT_REDIRECT_URL', "/")
ACCOUNT_EMAIL_SUBJECT_PREFIX = os.getenv('ACCOUNT_EMAIL_SUBJECT_PREFIX', '[Conflu] ')
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
# Add other email settings if using a real email backend (SMTP_HOST, etc.)
