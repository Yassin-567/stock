from django.shortcuts import render,redirect,HttpResponse, get_object_or_404
from .models import CustomUser,Company,Job,Item,Comment
from .forms import ItemForm,SearchForm,registerForm,loginForm,companyregisterForm,JobForm,CommentForm
from django.contrib.auth import authenticate, login, logout , update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib.auth.models import Group
from .decorators import admins_only,no_ban,owner_only
from django.db.models import F
from django.db.models import Count, Q
from django.forms import HiddenInput,MultipleHiddenInput
from django.forms import Select
from django import forms
from .myfunc import FormHandler, WareohuseFormHandler
from django.http import HttpResponseForbidden
from django.contrib.contenttypes.models import ContentType

#import requests


# from django.core.mail import send_mail



def logout_user(request):
    if not request.user.is_authenticated:
        messages.error(request, 'You are not logged in.')
        return redirect('login')
    logout(request)
    return redirect('login')

def login_user(request):
    form=loginForm()
    if request.user.is_authenticated:
        return redirect('inventory')
    if request.method == 'POST':
        form=loginForm(request.POST)
        username=request.POST['email']
        password=request.POST['password']
        user = authenticate(username=username, password=password)
        if user is not None and user.company is not None :
            login(request, user)
            return redirect('inventory')
        elif user.company is None:
            messages.error(request, "You aren't working in company")
            return render(request, 'auths/login.html', {'form': form})
        else:
            messages.error(request, 'Invalid login credentials')
            return render(request, 'auths/login.html', {'form': form})
    return render(request, 'auths/login.html', {'form': form})
#@admins_only
def register_user(request):
    
    if request.method == "POST":
        form = registerForm(request.POST,adding_worker=True)
        if form.is_valid():
            user = form.save(commit=False)  # Save user instance but don't commit yet
            user.set_password(form.cleaned_data['password'])  # Hash the password
            company = Company.objects.get(id=request.user.company.id)
            user.company = company
            # Ensure the user has a company before saving
            user.save()  # Save the user'
            user.groups.clear()
            group = form.cleaned_data['groups']
            print(group)
            user.groups.add(*group)  # Add user to the group
            messages.success(request, 'You have successfully registered')
            return redirect('register')  # Redirect after successful registration
        else:
            form = registerForm(adding_worker=True)
            messages.error(request, "Registration failed. Please check the form.")
    
    else:
        form = registerForm(adding_worker=True)

    return render(request, 'auths/register.html', {'form': form})
@login_required(login_url='login', redirect_field_name='inventory')
@no_ban
def inventory(request):
    rjobs = Job.objects.annotate(item_count=Count('items')).filter(items_arrived=True).prefetch_related('items')
    items=Item.objects.filter(company=request.user.company)
    
    rjobs=Job.objects.filter(company=request.user.company)
    
    context={'rjobs':rjobs,
            'items':items
            }
    return render(request,'inventory/inventory.html',context)

@login_required
def job_create(request):
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.company = request.user.company
            job.save()
            messages.success(request, 'Job created successfully')
            return redirect('inventory')
    else:
        form = JobForm()
    return render(request, 'inventory/job_create.html', {'form': form})
@login_required
def update_job(request, pk):
    job=Job.objects.filter(company=request.user.company).get(job_id=pk)
    items=Item.objects.filter(company=request.user.company,job=job)
    items_count=0
    for item in items:
        items_count+=item.job_quantity
    
    form = JobForm(instance=job,updating=True,)
    comments_form=CommentForm(initial={
        'content_type': ContentType.objects.get_for_model(Job),
        'object_id': job.job_id,
        'company': request.user.company,
        })
    comments = Comment.objects.filter(content_type=ContentType.objects.get_for_model(Job), object_id=job.job_id,company=request.user.company)
    
    if request.method == 'POST':
        comments_form=CommentForm(request.POST)
        form = JobForm(request.POST, instance=job,updating=True)
        
        if form.is_valid() and comments_form.is_valid():
            form.save()
            
            comment = comments_form.save(commit=False)
            comment.added_by = request.user 
            comment.company = request.user.company
            comment.save()
            comments = Comment.objects.filter(content_type=ContentType.objects.get_for_model(Job), object_id=job.job_id,company=request.user.company)
            messages.success(request, 'Job updated successfully')
            comments_form = CommentForm(initial={
        'content_type': ContentType.objects.get_for_model(Job),
        'object_id': job.job_id,
        'company': request.user.company,
        })
            form = JobForm(instance=job,)
            return render(request, 'inventory/job_update.html', {'form': form,'job':job,'comments_form':comments_form,'comments':comments})       
    context={'form': form,'job':job,'comments_form':comments_form,'comments':comments,'items':items,'items_count':items_count}
    return render(request, 'inventory/job_update.html', context)       
###########################ITEM######################
@login_required
def item_add(request,pk=None,no_job=False):
    try:
        job=Job.objects.filter(company=request.user.company).get(job_id=pk)
    except Job.DoesNotExist:
        job=None
    form=ItemForm()
    form.fields['job'].widget = MultipleHiddenInput()
    if request.method=='POST':
        form=ItemForm(request.POST)
        if form.is_valid():
            form.fields['job'].widget = MultipleHiddenInput()
            item=form.save(commit=False)
            item.company=request.user.company
            item.user=request.user
            item.added_by=request.user
            if pk is not None:
                try:
                    item.job = job
                    item.save()
                except Job.DoesNotExist:
                    messages.error(request, f'{pk}Specified job does not exist.')
                    return render(request, 'inventory/add_item.html', {'form': form})
            elif pk is None and no_job:
                item.job=None
                item.is_warehouse_item=True
                item.save(no_job=True)
            messages.success(request, 'Item added successfully')
            return redirect('inventory')
    return render(request, 'inventory/add_item.html', {'form': form,'job':job})
@login_required
def update_item(request, pk):
    item = Item.objects.get(id=pk)
    job=Job.objects.filter(company=request.user.company).get(job_id=item.job.job_id) if item.job else None
    completed=job.status=='completed'
    form = ItemForm(instance=item,updating=True,completed=completed)
    comments_form=CommentForm(initial={
        'content_type': ContentType.objects.get_for_model(Item),
        'object_id': item.id,
        'company': request.user.company,
        })
    comments= Comment.objects.filter(content_type=ContentType.objects.get_for_model(Item), object_id=item.id,company=request.user.company)
    if request.method == 'POST':
        comments_form=CommentForm(request.POST)
        if comments_form.is_valid() and "just_add_comment" in request.POST :
            
            comment = comments_form.save(commit=False)
            comment.added_by = request.user 
            comment.company = request.user.company
            comment.save()
            comments= Comment.objects.filter(content_type=ContentType.objects.get_for_model(Item), object_id=item.id,company=request.user.company)
            comments_form=CommentForm(initial={
        'content_type': ContentType.objects.get_for_model(Item),
        'object_id': item.id,
        'company': request.user.company,
        })
            context = {'form': form,'item': item,'comments_form':comments_form,"comments":comments,'completed':completed}
            return render(request, 'inventory/update_item.html', context)
        if "delete" in request.POST:
            itemname=item.name
            item.delete()
            messages.success(request, f"Item {itemname} deleted successfully.")
            return redirect('inventory')
        form = ItemForm(request.POST, request.FILES, instance=item,updating=True)
        if 'move_item' in request.POST :
            item.job=None
            item.is_moved_to_warehouse=True
            item.save(updating=True)
            return redirect('inventory')        
        form = ItemForm(request.POST, request.FILES, instance=item,updating=True)
        comments_form=CommentForm(request.POST)
        if form.is_valid() and 'edit' in request.POST: 
            item=form.save(commit=False)
            item.save(updating=True)
            form = ItemForm(request.POST, request.FILES, instance=item,updating=True)

            context = {'form': form,'item': item,'comments_form':comments_form,"comments":comments}
            return render(request, 'inventory/update_item.html', context)
    context = {'form': form,'item': item,'comments_form':comments_form,"comments":comments,"completed":completed}
    return render(request, 'inventory/update_item.html', context)
########################
@login_required
def update_warehouse_item(request, pk):
    item = Item.objects.filter(company=request.user.company,id=pk)[0]
    #job=Job.objects.filter(company=request.user.company).get(job_id=item.job.job_id) if item.job else None
    #completed=job.status=='completed'
    form = ItemForm(instance=item,updating=True)
    handler=WareohuseFormHandler(form,)
    handler.set_form_fields()
    comments_form=CommentForm(initial={
        'content_type': ContentType.objects.get_for_model(Item),
        'object_id': item.id,
        'company': request.user.company,
        })
    comments= Comment.objects.filter(content_type=ContentType.objects.get_for_model(Item), object_id=item.id,company=request.user.company)
    if request.method == 'POST':
        comments_form=CommentForm(request.POST)
        if comments_form.is_valid() and "just_add_comment" in request.POST :
            
            comment = comments_form.save(commit=False)
            comment.added_by = request.user 
            comment.company = request.user.company
            comment.save()
            comments= Comment.objects.filter(content_type=ContentType.objects.get_for_model(Item), object_id=item.id,company=request.user.company)
            comments_form=CommentForm(initial={
            'content_type': ContentType.objects.get_for_model(Item),
            'object_id': item.id,
            'company': request.user.company,
            })
            context = {'form': form,'item': item,'comments_form':comments_form,"comments":comments}
            return render(request, 'inventory/update_item.html', context)
        if "delete" in request.POST:
            itemname=item.name
            item.delete()
            messages.success(request, f"Item {itemname} deleted successfully.")
            return redirect('inventory')
        
        form = ItemForm(request.POST, request.FILES, instance=item,updating=True)
        handler=WareohuseFormHandler(form,)
        handler.set_form_fields()
        comments_form=CommentForm(request.POST)
        if form.is_valid() and 'edit' in request.POST: 
            item=form.save(commit=False)
            item.save(updating=True)
            form = ItemForm( instance=item,updating=True)
            handler=WareohuseFormHandler(form,)
            handler.set_form_fields()
            context = {'form': form,'item': item,'comments_form':comments_form,"comments":comments}
            return render(request, 'inventory/update_item.html', context)
    context = {'form': form,'item': item,'comments_form':comments_form,"comments":comments}
    return render(request, 'inventory/update_item.html', context)
    
@owner_only
@login_required
def update_company(request, pk):
    company = Company.objects.get(id=pk)
    form = companyregisterForm(instance=company,user=request.user,updating=True)
    if request.method == 'POST':
        form = companyregisterForm(request.POST ,request.FILES, instance=company,user=request.user)
        if form.is_valid():
            form.save()
            context = {'form': form,'company': company}
            messages.success(request,"Company updated successfuly")
            return render(request, 'inventory/update_company.html', context)
    context = {'form': form,'company': company}
    return render(request, 'inventory/update_company.html', context)


@admins_only
def admin_panel(request): 
        if request.user.groups.filter(name="Admin").exists() or request.user.company.owner==request.user:
            groups = Group.objects.all().order_by("name")
            context = {
                'groups': groups,
                'users': CustomUser.objects.filter(company=request.user.company),
            }
            return render(request, 'inventory/admin_panel.html',context )
        else:
            return HttpResponse("You are not authorized to view this page")
@no_ban
def update_user(request, pk):
    if request.user.company.owner==request.user or (request.user.groups.filter(name="Admin").exists() and CustomUser.objects.get(id=pk).groups.filter(name="Employee").exists()): 
        user = get_object_or_404(CustomUser, pk=pk)
        show_choices=True
    else:
        user = request.user
    form= registerForm(instance=user )
    handler = FormHandler(form,user=request.user,target_user=user,show_choices=show_choices)
    handler.set_form_fields()  
    context={
                "form":form,
                "user":user,
            }
    if request.method=="POST":
        form = registerForm(request.POST,instance=user) 
        handler = FormHandler(form,user=request.user,target_user=user,show_choices=show_choices)
        if form.is_valid():
            user = form.save(commit=False) 
            group = handler.get_user_group()
            if 'password' in form.cleaned_data and form.cleaned_data['password']:
                user.set_password(form.cleaned_data['password'])  
                user.save()
                user.groups.clear()
                if form.cleaned_data["is_banned"]:
                    group=Group.objects.get(name='Ban')
                user.groups.add(group)
                update_session_auth_hash(request, user)
                messages.success(request, "User updated successfully")
                user = get_object_or_404(CustomUser, pk=pk)
                
                handler.set_form_fields()              
                context={
                "form":form,
            }
            return render(request, 'inventory/update_user.html',context)  # Replace with actual view name
        else:
            messages.error(request,"Error")
            context={
            "form":form,
            "user":user,
            }
            return render(request, 'inventory/update_user.html',context)
    return render(request, 'inventory/update_user.html',context)


def register_company(request):
    """ Register a new company and its admin user """
    company_form = companyregisterForm(request.POST,user=request.user,)
    user_form = registerForm(request.POST,initial={'groups':'Owner'},registering=True)

    if request.method == 'POST':
        
        print(request.user)
        company_form = companyregisterForm(request.POST,)
        user_form = registerForm(request.POST,registering=True)
        if company_form.is_valid() and user_form.is_valid():
            
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data['password'])
            
            user.is_staff = True
            user.save()

            # Step 2: Now save the company and assign the owner
            company = company_form.save(commit=False)
            company.owner = user
            company.save()

            # Step 3: Update user with the company
            user.company = company
            user.save()

            # Step 3: Assign the user to the "Admin" group
            admin_group, _ = Group.objects.get_or_create(name='Admin')
            user.groups.clear()
            user.groups.add(admin_group)

            messages.success(request, 'Company and admin user registered successfully!')
        
        else:
            print ("not valid form")
            messages.error(request, f"Registration failed. Company Form Errors: {company_form.errors} User Form Errors: {user_form.errors}")
    else:
        company_form = companyregisterForm(user=request.user,initial={'group': "owner"})
        user_form = registerForm()

    return render(request, 'auths/register_company.html', {'company_form': company_form, 'user_form': user_form})
#############
def warehouse(request):
    warehouse_items=Item.objects.filter(is_warehouse_item=True ,company=request.user.company,)
    moved_items=Item.objects.filter(is_moved_to_warehouse=True ,company=request.user.company,)
    return render(request,'inventory/warehouse.html',{'warehouse_items':warehouse_items,'moved_items':moved_items})

def move_item(request,pk):
    item=Item.objects.filter(company=request.user.company,id=pk)[0]
    form = ItemForm(request.POST,instance=item,updating=True)
    print(1)
    if request.method=='POST':
        if "move_item" in request.POST:
            print(3)
    return HttpResponse("D")
import requests
from django.shortcuts import render

def fetch_api_data(request):
    url = "https://jsonplaceholder.typicode.com/posts"
    response = requests.get(url)
    data = response.json()  # Convert to dict

    return render(request, 'inventory/api_data.html', {'data': data})
#youssif_USF_SPY
