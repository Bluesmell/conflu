import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url # Ensures this import is present
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
dotenv_path = BASE_DIR / '.env'
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    # This print might be noisy in Docker logs if .env is only provided via docker-compose.yml
    # print(f"Warning: .env file not found at {dotenv_path}")
    pass # Keep it silent if not found, rely on env vars from docker-compose

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-defaultfallbacksecretkeyforcheck') # Key for 'check'
DEBUG_STR = os.getenv('DJANGO_DEBUG', 'True')
DEBUG = DEBUG_STR.lower() in ('true', '1', 't')

ALLOWED_HOSTS_ENV = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_ENV.split(',') if host.strip()]

INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'rest_framework', 'rest_framework_simplejwt', 'guardian',
    'core.apps.CoreConfig', 'users.apps.UsersConfig', 'workspaces.apps.WorkspacesConfig',
    'pages.apps.PagesConfig', 'attachments.apps.AttachmentsConfig', 'importer.apps.ImporterConfig',
    'llm_integrations.apps.LlmIntegrationsConfig', 'api.apps.ApiConfig',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'conflu_project_root_config.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [], 'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'conflu_project_root_config.wsgi.application'

DATABASES = {'default': dj_database_url.config(default=os.getenv('DATABASE_URL', 'sqlite:///./db_dev_fallback.sqlite3'), conn_max_age=600)}
CACHES = {'default': {'BACKEND': 'django_redis.cache.RedisCache', 'LOCATION': os.getenv('REDIS_URL', 'redis://localhost:6379/0'), 'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'}}}

AUTH_PASSWORD_VALIDATORS = [{'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},{'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE = 'en-us'; TIME_ZONE = 'UTC'; USE_I18N = True; USE_TZ = True
STATIC_URL = 'static/'; DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
REST_FRAMEWORK = {'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework_simplejwt.authentication.JWTAuthentication', 'rest_framework.authentication.SessionAuthentication'],'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticatedOrReadOnly'],'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination','PAGE_SIZE': 25}
SIMPLE_JWT = {'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15), 'REFRESH_TOKEN_LIFETIME': timedelta(days=7),'ROTATE_REFRESH_TOKENS': True, 'BLACKLIST_AFTER_ROTATION': False, 'UPDATE_LAST_LOGIN': True, 'ALGORITHM': 'HS256','AUTH_HEADER_TYPES': ('Bearer',), 'USER_ID_FIELD': 'id', 'USER_ID_CLAIM': 'user_id'}
