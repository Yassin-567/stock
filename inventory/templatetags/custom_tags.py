from django import template
from inventory.models import JobItem
from django.db.models import Q
register = template.Library()

@register.filter
def is_admin(user):
    if user.groups.filter(name='Admin').exists() or user.company.owner==user:
        return True
    return False
@register.filter
def is_in_group(user, group_name):
    
    return user.groups.filter(name=group_name).exists()
@register.filter
def is_owner(user):
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
    company=job.company
    job_items=JobItem.objects.filter(job=job)
    for jobitem in job_items:
        total_arrived_quantity+=jobitem.arrived_quantity
    return total_arrived_quantity
    # total_arrived_quantity = 0
    # for item in job.items.all():
    #     total_arrived_quantity = total_arrived_quantity+item.arrived_quantity
    # return total_arrived_quantity
        