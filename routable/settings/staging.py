# Sentry
import dj_database_url

from .base import *

DEBUG = False

# Set environment variable for the DB in the staging environment
DATABASES['default'] = dj_database_url.config(env='DATABASE_URL', conn_max_age=600)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}
