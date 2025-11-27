import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
if config('RENDER_EXTERNAL_HOST', default=''):
    ALLOWED_HOSTS.append(config('RENDER_EXTERNAL_HOST'))

INSTALLED_APPS = ['bot']

MIDDLEWARE = ['django.middleware.common.CommonMiddleware']

ROOT_URLCONF = 'communal_bot.urls'

DATABASES = {'default': {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': config('DB_NAME', default='communal_bot'),
    'USER': config('DB_USER', default=''),
    'PASSWORD': config('DB_PASSWORD', default=''),
    'HOST': config('DB_HOST', default='localhost'),
    'PORT': config('DB_PORT', default='5432'),
}}

if config('DATABASE_URL', default=''):
    import dj_database_url
    DATABASES['default'] = dj_database_url.parse(config('DATABASE_URL'))

USE_TZ = True
TIME_ZONE = 'UTC'
USE_I18N = False

STATIC_URL = '/static/'

TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN')
ADMIN_TELEGRAM_IDS = set(int(x.strip()) for x in config('ADMIN_TELEGRAM_IDS', default='').split(',') if x.strip())

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
}