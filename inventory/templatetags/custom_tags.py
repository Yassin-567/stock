from django import template
from inventory.models import JobItem,Job,WarehouseItem,Category,CustomUser,Engineer,Company
from django.urls import reverse
from django.db.models import Q
register = template.Library()
from django.shortcuts import redirect

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

@register.filter
def get_link(obj):
    
    if isinstance(obj, Job):
        return reverse('update_job', args=[obj.job_id])
    elif isinstance(obj, JobItem):
        return reverse('update_item', args=[obj.id])
    elif isinstance(obj, Company):
        return reverse('update_company')
   
   
    elif isinstance(obj, JobItem):
        return reverse('update_item', args=[obj.id])
    elif isinstance(obj, WarehouseItem):
        return reverse('update_warehouse_item', args=[obj.id])  # adjust field name
    else:
        return ""  # fallback if unknown type
    
@register.filter
def trim(value):
    try:
        return value.strip()
    except Exception:
        return value
    
@register.filter
def integerme(value):
    try:
        return int(value)
    except Exception:
        return value
    
from django.utils import timezone

@register.filter
def days(value):
    """
    Returns the number of days between today and the given date.
    """
    if not value:
        return ""
    
    now = timezone.now().date()
    if hasattr(value, 'date'):  # handle datetime
        value = value.date()
    
    delta = now - value
    return delta.days
@register.filter
def days_float(value):
    """Return age in days with fractions (e.g., 6.5 days)."""
    if not value:
        return None
    delta = timezone.now() - value
    return delta.total_seconds() / 86400  # 86400 seconds in a day