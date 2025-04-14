from django import template

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