# Sentry
import dj_database_url

from .base import *

DEBUG = False

# If we are running on HEROKU, otherwise use a different environment variable
DATABASES['default'] = dj_database_url.config(env='HEROKU_POSTGRESQL_URL', conn_max_age=600)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache',
        'TIMEOUT': 172800,
        'OPTIONS': {
            'MAX_ENTRIES': 1000000,
            'CULL_FREQUENCY': 2
        }
    }
}
