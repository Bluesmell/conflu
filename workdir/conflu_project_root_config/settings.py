import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url
from datetime import timedelta
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

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
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'rest_framework', 'rest_framework_simplejwt',
    'guardian', # django-guardian
    'drf_spectacular', 'drf_spectacular_sidecar',
    'storages',
    'core.apps.CoreConfig', 'users.apps.UsersConfig', 'workspaces.apps.WorkspacesConfig',
    'pages.apps.PagesConfig', 'attachments.apps.AttachmentsConfig', 'importer.apps.ImporterConfig',
    'llm_integrations.apps.LlmIntegrationsConfig', 'api.apps.ApiConfig',
]

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend', # Default
    'guardian.backends.ObjectPermissionBackend', # django-guardian
)

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework_simplejwt.authentication.JWTAuthentication', 'rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticatedOrReadOnly'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}
SIMPLE_JWT = {'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15), 'REFRESH_TOKEN_LIFETIME': timedelta(days=7),'ROTATE_REFRESH_TOKENS': True, 'BLACKLIST_AFTER_ROTATION': False, 'UPDATE_LAST_LOGIN': True, 'ALGORITHM': 'HS256','AUTH_HEADER_TYPES': ('Bearer',), 'USER_ID_FIELD': 'id', 'USER_ID_CLAIM': 'user_id'}

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
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_STORAGE_BUCKET_NAME:
        DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    else:
        DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
        MEDIA_ROOT = PROJECT_ROOT_DIR / 'mediafiles_data_fallback'
        os.makedirs(MEDIA_ROOT, exist_ok=True)
else: # local storage
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_ROOT = PROJECT_ROOT_DIR / 'mediafiles_data'
    os.makedirs(MEDIA_ROOT, exist_ok=True)
