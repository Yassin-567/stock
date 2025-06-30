from django import template
from inventory.models import JobItem
from django.db.models import Q
register = template.Library()

@register.filter
def is_admin(user):
    try:
        company=user.company
    except:
        company=None
    if company and user.is_authenticated:
        if user.company.owner==user or user.is_admin:
            return True
    return False

@register.filter
def is_owner(user):
    try:
        company=user.company
    except:
        company=None
    if company and user.is_authenticated:
        if user.is_authenticated and user.company.owner==user:
            return True
    return False
   
# filepath: c:\Users\3Y\Desktop\venv1\stock\inventory\templatetags\custom_tags.py
from django import template


@register.filter
def add_suffix(value, suffix):
    if value:
        return f"{value}{suffix}"
    return ""

@register.filter
def total_quantity(job):

    total_quantity = 0
    for item in job.items.all():
        total_quantity =total_quantity+item.job_quantity
    return total_quantity

@register.filter
def total_arrived_quantity(job):
    total_arrived_quantity=0
    job_items=JobItem.objects.filter(job=job)
    for jobitem in job_items:
        total_arrived_quantity+=jobitem.arrived_quantity
    return total_arrived_quantity
    # total_arrived_quantity = 0
    # for item in job.items.all():
    #     total_arrived_quantity = total_arrived_quantity+item.arrived_quantity
    # return total_arrived_quantity

@register.filter
def parent_path(value):
    # Remove query string if present
    path = value.split('?')[0]
    # Remove trailing slash for easier processing
    if path.endswith('/') and path != '/':
        path = path[:-1]
    # Split the path and check the last segment
    segments = path.rsplit('/', 1)
    if len(segments) == 2 and segments[1] == '1':
        return segments[0] + '/'
    return value  # Return original if not ending with '1' or '1/'
@register.filter
def all_not_used(job):
    if job.items.exclude(is_used=True).exists():
        return True