import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'communal-bot.onrender.com']
# if config('RENDER_EXTERNAL_HOST', default=''):
#     ALLOWED_HOSTS.append(config('RENDER_EXTERNAL_HOST'))
RENDER_EXTERNAL_HOST = os.environ.get('RENDER_EXTERNAL_HOST')
if RENDER_EXTERNAL_HOST:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOST)

INSTALLED_APPS = ['bot']

MIDDLEWARE = ['django.middleware.common.CommonMiddleware']

ROOT_URLCONF = 'communal_bot.urls'

DATABASES = {}
if config('DATABASE_URL', default=''):
    import dj_database_url
    DATABASES['default'] = dj_database_url.parse(config('DATABASE_URL'))
else:
    # Для локальной разработки (SQLite)
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }

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