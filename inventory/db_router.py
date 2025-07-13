# inventory/db_router.py

import sys
import threading
from django.conf import settings
from django.db import connections

_thread_locals = threading.local()

def get_current_db():
    """Determine the current DB context based on thread-local or CLI commands."""
    if any(cmd in sys.argv for cmd in ['migrate', 'makemigrations', 'collectstatic', 'createsuperuser']):
        return 'default'
    return getattr(_thread_locals, 'db', 'default')


class CompanyRouter:
    def route_model(self, model):
        model_name = model._meta.model_name.lower()
        if model_name in self.tenant_models:
            return get_current_db()
        return 'default'
    tenant_models = {
        'Job', 'jobitem', 'warehouseitem', 'item', 'engineer', 'comment', 'category'
    }

    def db_for_read(self, model, **hints):
        return self.route_model(model)

    def db_for_write(self, model, **hints):
        return self.route_model(model)

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return True
        if db == 'default':
            return True

        if db.startswith('client_'):
            if model_name:
                return model_name.lower() in self.tenant_models
            return False  # or None, depending on your intent

        return None

        