from django.http import HttpResponse
from functools import wraps
from django.contrib import messages
from django.shortcuts import render,redirect
from .forms import loginForm
from . import views
def admins_only(view_func):
    @wraps(view_func)
    def wrapper_func(request, *args, **kwargs):
        if request.user.groups.filter(name="Admin").exists() or request.user.company.owner==request.user:
            print("User is an Admin")
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponse("You are not authorized to view this page")
    return wrapper_func  # Return the modified function


def no_ban(view_func):
    @wraps(view_func)
    def wrapper_func(request, *args, **kwargs):
        # Check if the user is banned
        if not request.user.company.owner==request.user :
            if request.user.groups.filter(name="Ban").exists():
                messages.error(request, f'<span style="color: red; font-weight: bold;">{request.user.username}</span> is banned from {request.user.company.company_name}')
                session=request.session
                session.clear()
                return redirect('login')
            else:
                return view_func(request, *args, **kwargs)
        return view_func(request, *args, **kwargs)
    return wrapper_func  # Return the modified function


def owner_only(view_func):
    def wrapper_func(request, *args, **kwargs):
        if request.user.is_authenticated:      
            if   not request.user.company_owner==request.user or request.user.company==None:
                 return view_func(request, *args, **kwargs)
            return redirect('inventory')
        return redirect('login')
    return wrapper_func