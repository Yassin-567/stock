# utils.py
from django.db import connections
from django.conf import settings
from django.core.management import call_command
from copy import deepcopy
from .models import Company, CustomUser
from django.db.migrations.executor import MigrationExecutor

def migrate_client_db(settings_obj):
    
    alias = f'client_{settings_obj.company.id}'
    
    # connections.databases[alias] = {
    #     'ENGINE': 'django.db.backends.postgresql',
    #     'NAME': settings_obj.db_name,
    #     'USER': settings_obj.db_user,
    #     'PASSWORD': settings_obj.db_pass,
    #     'HOST': settings_obj.db_host,
    #     'PORT': settings_obj.db_port,
    #     'OPTIONS': {},
    #     'ATOMIC_REQUESTS': False,
    #     'AUTOCOMMIT': True,
    #     'TIME_ZONE': settings.TIME_ZONE,
    #     'CONN_HEALTH_CHECKS': False,
    #     'CONN_MAX_AGE': 0,
    #     'DISABLE_SERVER_SIDE_CURSORS': False,
    #     'TEST': {
    #         'CHARSET': None,
    #         'COLLATION': None,
    #         'MIRROR': None,
    #         'NAME': None,
    #                     }
    # }
    connections.databases[alias] ={
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'stocky-db',
        'USER': 'yassin',
        'PASSWORD': '123',
        'HOST': 'localhost',
        'PORT': '5432',
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
                        }}
    print(alias)
    call_command('migrate', database=alias)

from inventory.models import Company, CustomUser, Job, Item, JobItem
from django.db.models import Count, Q
# def seed_company_and_users(settings_obj,company_id, ):
#     pass
#     CustomUser.objects.create(
#         company=company
#     )
    
#     company = Company.objects.get(id=company_id)
#     alias = f'client_{settings_obj.company.id}'
    
#     target_alias = connections[alias]
#     target_alias=target_alias.alias
    
    # Copy Company
    # owner=CustomUser.objects.get(Q(company=company)&Q(is_owner=True))

    # original_owner = company.owner
    # company.owner = None
    # company.save(using=target_alias)

    # # STEP 2: Save owner (it references the already-saved company now)
    # owner.company = company
    # owner.save(using=target_alias)

    # # STEP 3: Now update the company with its correct owner
    # company.owner = original_owner
    # company.save(using=target_alias)
    # Copy Users
    # for user in CustomUser.objects.filter(company=company):
    #     user.pk = user.id
    #     user.save(using=target_alias)

    # # Copy Jobs
    # for job in Job.objects.filter(company=company):
    #     job.pk = job.id
    #     job.save(using=target_alias)

    # Same for Item, JobItem, Engineer, etc.
