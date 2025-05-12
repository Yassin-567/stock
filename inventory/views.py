from django.shortcuts import render,redirect,HttpResponse, get_object_or_404
from .models import CustomUser,Company,Job,Item,Comment,JobItem,WarehouseItem,Engineer
from .forms import ItemForm,SearchForm,registerForm,loginForm,companyregisterForm,JobForm,CommentForm,StokcItemsForm,JobItemForm,WarehouseitemForm,EngineerForm
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
from .myfunc import FormHandler, WareohuseFormHandler, calculate_item
from django.http import HttpResponseForbidden
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from django.core.mail import send_mail

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
            'items':items,
            }
    return render(request,'inventory/inventory.html',context)

@login_required
def job_create(request):
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            try:
                Job.objects.get(job_id=form.cleaned_data['job_id'])
                jobi=True
            except Job.DoesNotExist:
                jobi=False
            if not jobi:
                job = form.save(commit=False)
                job.company = request.user.company
                job.save()
                messages.success(request, 'Job created successfully')
            else:
                messages.error(request,"This job already exists")
            return redirect('inventory')
    else:
        form = JobForm()
    return render(request, 'inventory/job_create.html', {'form': form})
@login_required
def update_job(request, pk):
    job=Job.objects.filter(company=request.user.company).get(job_id=pk)
    items=JobItem.objects.filter(job=job)
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
    
    if request.method == 'POST' and 'save' in request.POST:
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
            items=JobItem.objects.filter(job=job)
    if request.method == 'POST' and 'send_email' in request.POST :
            if job.engineer is not None and job.status=="ready":
                recipient_list=[]
                recipient_list.append(job.engineer.email)
                # parts=[]
                # for part in job.items.all():
                #     parts.append(part)
                parts = [str(part) for part in job.items.all()]
                parts_text = "\n".join(parts)
                print(parts)
                print(parts_text)
                send_mail(
                    subject=f'Job {job.address}',
                    message=f'Hi, please take the following parts:\n\n{parts_text}',
                    from_email='yassinalaa3310@gmail.com',
                    recipient_list=['yassinalaa3310@gmail.com'],
                    fail_silently=False,
                )
                
                messages.success(request,f'Email sent to {job.engineer.name}')
                form = JobForm(instance=job,updating=True,)
                comments_form=CommentForm(initial={
                    'content_type': ContentType.objects.get_for_model(Job),
                    'object_id': job.job_id,
                    'company': request.user.company,
                    })
                comments = Comment.objects.filter(content_type=ContentType.objects.get_for_model(Job), object_id=job.job_id,company=request.user.company)
                
                return render(request, 'inventory/job_update.html', {'form': form,'job':job,'comments_form':comments_form,'comments':comments,'items':items,'items_count':items_count})       
            messages.error(request,"ddd")
            comments = Comment.objects.filter(content_type=ContentType.objects.get_for_model(Job), object_id=job.job_id,company=request.user.company)
            comments_form = CommentForm(initial={
            'content_type': ContentType.objects.get_for_model(Job),
            'object_id': job.job_id,
            'company': request.user.company,
            })
            form = JobForm(instance=job,)
            items=JobItem.objects.filter(job=job)
            return render(request, 'inventory/job_update.html', {'form': form,'job':job,'comments_form':comments_form,'comments':comments,'items':items,'items_count':items_count})       
    context={'form': form,'job':job,'comments_form':comments_form,'comments':comments,'items':items,'items_count':items_count}
    return render(request, 'inventory/job_update.html', context)       
###########################ITEM######################
@login_required
def item_add(request,pk=None,no_job=False):
    try:
        job=Job.objects.filter(company=request.user.company).get(job_id=pk)
    except Job.DoesNotExist:
        job=None
    
    form=ItemForm(job=job)
    stock_items_form=StokcItemsForm(company=request.user.company)
    #form.fields['job'].widget = MultipleHiddenInput() 
    # if job is None:
    #     form.fields['job_quantity'].widget = HiddenInput()
    # else:
    #     form.fields['job_quantity'].widget = forms.TextInput()
    if request.method=='POST':
        if pk is not None:
            stock_items_form=StokcItemsForm(request.POST,company=request.user.company)
        form=ItemForm(request.POST)
        if 'adding_from_stock' in request.POST:
            if stock_items_form.is_valid():
                stock_items=stock_items_form.cleaned_data['stock_items'] 
                required_quantity=stock_items_form.cleaned_data['required_quantity'] 
                if len(stock_items)>0:
                    for item in stock_items:
                        
                        try:
                            with transaction.atomic():
                                
                                if item.warehouse_quantity>0 and item.warehouse_quantity>= required_quantity:
                                    if JobItem.objects.filter(job=job,item=item.item,):
                                        jobitem=JobItem.objects.filter(job=job,item=item.item,).first()
                                        jobitem.job_quantity=jobitem.job_quantity+required_quantity
                                        jobitem.arrived_quantity=jobitem.job_quantity
                                        jobitem.save(update_fields=['job_quantity'])
                                        item.warehouse_quantity=item.warehouse_quantity-required_quantity
                                        item.save(update_fields=['warehouse_quantity'])
                                    else:
                                        JobItem.objects.create(
                                        job=job,
                                        from_warehouse=True,
                                        item=item.item,
                                        status='arrived',
                                        job_quantity=+required_quantity,
                                        arrived_quantity=+required_quantity,
                                        )
                                        item.warehouse_quantity=item.warehouse_quantity-required_quantity
                                        item.save(update_fields=['warehouse_quantity'])
                                        print(item.warehouse_quantity)
                                else:
                                    messages.error(request,"Not enough stock")
                                    return redirect('inventory')
                        except IntegrityError:
                            messages.error(request,"Failed")
                        # item.job=job
                        # item.is_warehouse_item=True
                        # item.save()
                        # calculate_item(item=item,job_qunatity=job_quantity)
                        
                    messages.success(request, 'Item added from stock successfully')
                    form=ItemForm(job=job)
                    stock_items_form=StokcItemsForm(company=request.user.company)
                    return render(request, 'inventory/add_item.html', {'form': form,'job':job,'stock_items_form':stock_items_form})
        elif 'adding_new' in request.POST:
            if form.is_valid():
                
                try:
                    with transaction.atomic():
                        
                        
                        job_quantity=form.cleaned_data['required_quantity']
                        arrived_quantity=form.cleaned_data['arrived_quantity']
                        if pk is not None:
                            item=form.save(commit=False)
                            item.company=request.user.company
                            
                            item.added_by=request.user
                            
                            item.save()
                            
                            job=Job.objects.filter(company=request.user.company).get(job_id=pk)

                            JobItem.objects.create(item=item,
                                                job=job,
                                                job_quantity=job_quantity,
                                                arrived_quantity=arrived_quantity,
                                                
                                                )
                            #item.job = job
                            #item.save()
                            form=ItemForm(job=job)
                            stock_items_form=StokcItemsForm(company=request.user.company)
                            messages.success(request, f'{item}-is added to job {job}')
                            return render(request, 'inventory/add_item.html', {'form': form,'stock_items_form':stock_items_form})
                        elif pk is None and no_job: 

                            item=form.save(commit=False)
                            
                            pn=form.cleaned_data['part_number']
                            try:

                                item_queryset = WarehouseItem.objects.get(item=Item.objects.get(Q(part_number=pn) & Q(company=request.user.company)))
                            except :
                                item_queryset=False
                            print(item_queryset)
                            print(item)
                            if item_queryset :
                                item=WarehouseItem.objects.get(item=Item.objects.get(Q(part_number=pn) & Q(company=request.user.company)))
                                item.warehouse_quantity+=arrived_quantity
                                item.save(update_fields=['warehouse_quantity'])
                            else:
                                item=form.save(commit=False)
                                item.company=request.user.company
                                item.added_by=request.user
                                item.save()
                                WarehouseItem.objects.create(item=item,
                                                        warehouse_quantity=arrived_quantity,
                                                        company=request.user.company,)
                            messages.success(request, f'{item}-is added to warehouse')
                            return redirect('inventory')
                except IntegrityError:
                    messages.error(request, f'{item} — failed')
                # Raise an IntegrityError manually to roll back the transaction
                    #raise IntegrityError("Job does not exist, rolling back item save.")
                    return render(request, 'inventory/add_item.html', {'form': form,'job':job,'stock_items_form':stock_items_form})
    return render(request, 'inventory/add_item.html', {'form': form,'job':job,'stock_items_form':stock_items_form})
@login_required
def update_item(request, pk):
    item = JobItem.objects.get(Q(id=pk) & Q(job__company=request.user.company))
    job=Job.objects.filter(company=request.user.company).get(job_id=item.job.job_id) if item.job else None
    completed=job.status=='completed'
    form = JobItemForm(instance=item,item=item)#,updating=True,completed=completed
    comments_form=CommentForm(initial={
        'content_type': ContentType.objects.get_for_model(JobItem),
        'object_id': item.id,
        'company': request.user.company,
        })
    comments= Comment.objects.filter(content_type=ContentType.objects.get_for_model(JobItem), object_id=item.id,company=request.user.company)
    if request.method == 'POST':
        comments_form=CommentForm(request.POST)
        if comments_form.is_valid() and "just_add_comment" in request.POST :
            comment = comments_form.save(commit=False)
            comment.added_by = request.user 
            comment.company = request.user.company
            comment.save()
            comments= Comment.objects.filter(content_type=ContentType.objects.get_for_model(JobItem), object_id=item.id,company=request.user.company)
            comments_form=CommentForm(initial={
        'content_type': ContentType.objects.get_for_model(JobItem),
        'object_id': item.id,
        'company': request.user.company,
        })
            context = {'form': form,'item': item,'comments_form':comments_form,"comments":comments,'completed':completed}
            return render(request, 'inventory/update_item.html', context)
        if "delete" in request.POST:
            itemname=item.item.name
            item.item.delete()
            item.delete()
            messages.success(request, f"Item {itemname} deleted successfully.")
            return redirect('inventory')
        form = ItemForm(request.POST, request.FILES, instance=item,updating=True)
        if 'move_item' in request.POST :
            try:
                job_item = JobItem.objects.get(id=item.id)

                # Optional: Check if already used or empty
                if job_item.is_used or job_item.arrived_quantity == 0:
                    print('used?',job_item.is_used)
                    print('used?',job_item.arrived_quantity)
                    messages.error(request, "Nothing to move or already used.")
                    form = JobItemForm(instance=item,item=item)
                    comments_form=CommentForm(initial={
        'content_type': ContentType.objects.get_for_model(JobItem),
        'object_id': item.id,
        'company': request.user.company,
        })
                    context = {'form': form,'item': item,'comments_form':comments_form,"comments":comments,'completed':completed}
                    return render(request, 'inventory/update_item.html', context)
                if not job_item.from_warehouse :
                    # Create WarehouseItem
                    WarehouseItem.objects.create(
                        item=job_item.item,
                        warehouse_quantity=job_item.arrived_quantity,
                        company=request.user.company,
                        #is_used=job_item.is_used,
                        is_moved_from_job=True 
                    )
                else:
                    
                    wi=WarehouseItem.objects.get(item=job_item.item)
                    wi.warehouse_quantity+=job_item.arrived_quantity
                    wi.save(update_fields=['warehouse_quantity'])
                # Delete JobItem after successful move
                job_item.delete()
                messages.success(request,"Item moved to warehouse")
            except JobItem.DoesNotExist:
                messages.error(request,"Moving failed")
            return redirect('inventory') 
       
        form = JobItemForm(request.POST, request.FILES, instance=item,item=item)
        comments_form=CommentForm(request.POST)
        prevq=item.job_quantity
        if form.is_valid() and 'edit' in request.POST: 
            job_quantiy=form.cleaned_data['job_quantity']
            if item.from_warehouse:
                if WarehouseItem.objects.get(item=item.item).warehouse_quantity>=job_quantiy-prevq:
                    
                    # if job_quantiy>prevq:
                    witem=WarehouseItem.objects.get(item=item.item)
                    witem.warehouse_quantity+=prevq-job_quantiy
                    witem.save(update_fields=['warehouse_quantity'])

                    # else:
                    #     print(job_quantiy,prevq,"less")
                    item=form.save(commit=False)
                    item.save()
                    
                else:
                    witem=WarehouseItem.objects.get(item=item.item)
                    form = JobItemForm( instance=item,item=item)
                    messages.error(request,f"Not enough stock, only {witem.warehouse_quantity} available")
                    context = {'form': form,'item': item,'comments_form':comments_form,"comments":comments}
                    return render(request, 'inventory/update_item.html', context)
            else:
                item=form.save(commit=False)
                item.save()
            
            form = JobItemForm( instance=item,item=item)#request.POST, request.FILES,updating=True

            context = {'form': form,'item': item,'comments_form':comments_form,"comments":comments}
            return render(request, 'inventory/update_item.html', context)
    context = {'form': form,'item': item,'comments_form':comments_form,"comments":comments,"completed":completed}
    return render(request, 'inventory/update_item.html', context)
########################
@login_required
def update_warehouse_item(request, pk):
    item = WarehouseItem.objects.filter(company=request.user.company,id=pk)[0].item
    warehouse_item = WarehouseItem.objects.filter(company=request.user.company,id=pk)[0]
    
    #job=Job.objects.filter(company=request.user.company).get(job_id=item.job.job_id) if item.job else None
    #completed=job.status=='completed'
    form =WarehouseitemForm(instance=item,warehouse_item=warehouse_item)#,updating=True
    # handler=WareohuseFormHandler(form,)
    # handler.set_form_fields(warehouse_item=warehouse_item)
    comments_form=CommentForm(initial={
        'content_type': ContentType.objects.get_for_model(WarehouseItem),
        'object_id': warehouse_item.id,
        'company': request.user.company,
        })
    comments= Comment.objects.filter(content_type=ContentType.objects.get_for_model(WarehouseItem), object_id=warehouse_item.id,company=request.user.company)
    if request.method == 'POST':
        comments_form=CommentForm(request.POST)
        if comments_form.is_valid() and "just_add_comment" in request.POST :
            
            comment = comments_form.save(commit=False)
            comment.added_by = request.user 
            comment.company = request.user.company
            comment.save()
            comments= Comment.objects.filter(content_type=ContentType.objects.get_for_model(WarehouseItem), object_id=warehouse_item.id,company=request.user.company)
            comments_form=CommentForm(initial={
            'content_type': ContentType.objects.get_for_model(Item),
            'object_id': warehouse_item.id,
            'company': request.user.company,
            })
            context = {'form': form,'item': item,'comments_form':comments_form,"comments":comments}
            return render(request, 'inventory/update_item.html', context)
        if "delete" in request.POST:
            # itemname=item.name
            # item.delete()
            # messages.success(request, f"Item {itemname} deleted successfully.")
            messages.success(request, f"Oops deleting isn't available now")
            return redirect('inventory')
        
        form = WarehouseitemForm(request.POST, request.FILES, instance=item,warehouse_item=warehouse_item)
        # handler=WareohuseFormHandler(form,)
        # handler.set_form_fields()
        comments_form=CommentForm(request.POST)
        if form.is_valid() and 'edit' in request.POST: 
            item=form.save(commit=False)
            item.company=request.user.company
            item.save(update_fields=['arrived_quantity'],)#updating=True
            arrived_quantity=form.cleaned_data['arrived_quantity']
            warehouse_item.warehouse_quantity=arrived_quantity
            warehouse_item.save(update_fields=['warehouse_quantity'])
            form = WarehouseitemForm( instance=item,warehouse_item=warehouse_item)
            
            messages.success(request,f'Item {warehouse_item} updated successfully')
            context = {'form': form,'item': item,'comments_form':comments_form,"comments":comments}
            return render(request, 'inventory/update_item.html', context)
    context = {'form': form,'item': item,'comments_form':comments_form,"comments":comments}
    return render(request, 'inventory/update_item.html', context)
    
@owner_only
@login_required
def update_company(request,):
    company = request.user.company
    form = companyregisterForm(instance=company,user=request.user,updating=True,enable_edit=False)

    if request.method=='POST' and 'edit' in request.POST:
        
        form = companyregisterForm(instance=company,user=request.user,updating=True,enable_edit=True)
        
        context = {'form': form,'company': company,'enable_edit':True}
        return render(request, 'inventory/update_company.html', context)
    


    if request.method == 'POST' and 'save' in request.POST:
        
        form = companyregisterForm(request.POST ,request.FILES, instance=company,user=request.user,enable_edit=False)
        if form.is_valid():
            form.save()
            
            form = companyregisterForm(instance=company,user=request.user,updating=True,enable_edit=False)
            context = {'form': form,'company': company,'enable_edit':False}
            messages.success(request,"Company updated successfuly")
            return render(request, 'inventory/update_company.html',context)
    
    
    context = {'form': form,'company': company,'enable_edit':False}
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
    company_form = companyregisterForm(user=request.user,)
    user_form = registerForm(registering=True)

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
    # else:
    #     company_form = companyregisterForm(user=request.user,initial={'group': "owner"})
    #     user_form = registerForm(request.POST,registering=True)

    return render(request, 'auths/register_company.html', {'company_form': company_form, 'user_form': user_form})
#############
def warehouse(request):
    warehouse_items=WarehouseItem.objects.filter(company=request.user.company)
    moved_items=WarehouseItem.objects.filter(is_moved_from_job=True ,company=request.user.company)
    used_warehouse_items=WarehouseItem.objects.filter(company=request.user.company,is_used=True)
    used_moved_items=WarehouseItem.objects.filter(is_moved_from_job=True ,company=request.user.company,is_used=True)
    
    return render(request,'inventory/warehouse.html',{'warehouse_items':warehouse_items,'moved_items':moved_items,'used_warehouse_items':used_warehouse_items,'used_moved_items':used_moved_items})

def engineer(request):
    form=EngineerForm()
    if request.method=="POST":
       # form=EngineerForm(request)
       # if form.is_valid:
         #   form.save(commit=False)
            #form.company=request.user.company
            #form.save
            messages.error(request,"Adding engineers isn't currently available")
            return render(request,'inventory/eng.html',{'form':form})
    return render(request,'inventory/eng.html',{'form':form})
import requests
from django.shortcuts import render

def fetch_api_data(request):
    url = "https://jsonplaceholder.typicode.com/posts"
    response = requests.get(url)
    data = response.json()  # Convert to dict

    return render(request, 'inventory/api_data.html', {'data': data})
#youssif_USF_SPY