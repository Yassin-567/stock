# inventory/middleware.py

import sys
import threading
from django.conf import settings
from django.db import connections

_thread_locals = threading.local()

# -----------------------------
# DB Context Setters & Getters
# -----------------------------
def set_current_db(db_key):
    """Set the current database key for this thread."""
    _thread_locals.db = db_key

def get_current_db():
    """Return the active DB key. Force 'default' during CLI commands."""
    if any(cmd in sys.argv for cmd in ['migrate', 'makemigrations', 'collectstatic', 'createsuperuser']):
        return 'default'
    return getattr(_thread_locals, 'db', 'default')

# -----------------------------
# Middleware for Dynamic DBs
# -----------------------------
class DynamicDBMiddleware:
    """Middleware to switch DB based on the logged-in user's company."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        db_key = 'default'

        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            company = getattr(user, 'company', None)
            settings_obj = getattr(company, 'settings', None)

            if settings_obj and settings_obj.use_own_db:
                db_key = f'client_{company.id}'

                # Create DB config for the tenant if not already added
                if db_key not in connections.databases:
                    connections.databases[db_key] = {
                        'ENGINE': 'django.db.backends.postgresql',
                        'NAME': settings_obj.db_name,
                        'USER': settings_obj.db_user,
                        'PASSWORD': settings_obj.db_pass,
                        'HOST': settings_obj.db_host,
                        'PORT': settings_obj.db_port,
                        'OPTIONS': {},
                        'ATOMIC_REQUESTS': False,
                        'AUTOCOMMIT': True,
                        'TIME_ZONE': settings.TIME_ZONE,
                        'CONN_HEALTH_CHECKS': False,
                        'CONN_MAX_AGE': 0,
                        'DISABLE_SERVER_SIDE_CURSORS': False,
                        'TEST': {
                            'CHARSET': None,
                            'COLLATION': None,
                            'MIRROR': None,
                            'NAME': None,
                        }
                    }

        set_current_db(db_key)
        return self.get_response(request)
