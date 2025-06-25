from django.shortcuts import render,redirect,HttpResponse, get_object_or_404
from .models import CustomUser,Company,Job,Item,Comment,JobItem,WarehouseItem,Engineer
from .forms import ItemForm,SearchForm,registerForm,loginForm,companyregisterForm,JobForm,CommentForm,StokcItemsForm,JobItemForm,WarehouseitemForm,EngineerForm,registerworker
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
from django.http import HttpResponseForbidden
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from django.core.mail import send_mail
from django.core.paginator import Paginator


#import requests


# from django.core.mail import send_mail


@login_required(login_url='login', redirect_field_name='inventory')
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

@admins_only
def register_user(request):
    
    if request.method == "POST":
        form = registerworker(request.POST,)
        
        if form.is_valid():
            user = form.save(commit=False)  # Save user instance but don't commit yet
            user.set_password(form.cleaned_data['password'])  # Hash the password
            company = Company.objects.get(id=request.user.company.id)
            user.company = company
            # Ensure the user has a company before saving
            user.save()  # Save the user'
            
            messages.success(request, 'You have successfully registered a new user')
            return redirect('register')  # Redirect after successful registration
        else:
            form = registerworker()
            messages.error(request, "Registration failed. Please check the form.")
    else:
        form = registerworker()
    return render(request, 'auths/register.html', {'form': form})
@login_required(login_url='login', redirect_field_name='inventory')
@no_ban
def inventory(request,pk=None):
    

    rjobs = Job.objects.annotate(item_count=Count('items')).filter(items_arrived=True).prefetch_related('items')
    
    rjobs=Job.objects.filter(company=request.user.company)
    paginator=Paginator(rjobs,10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context={
            
            'rjobs': page_obj,
            'page_obj':page_obj
            }
    if request.method=='POST' and "reset_notes" in request.POST:
        jobitem=JobItem.objects.get(id=pk)
        # item=Item.objects.get(id=jobitem.item.id)
        jobitem.notes=None
        jobitem.is_used=False
        jobitem.save(update_fields=['is_used','notes'])
        jobitem.job.save(update_fields=['status','items_arrived'])
    elif request.method=="POST" and 'job_is_ready' in request.POST:
        job=Job.objects.get(job_id=pk,company=request.user.company)
        if job.items.exclude(is_used=False).exists():
            messages.error(request,'There is a used item')
            return render(request,'inventory/inventory.html',context)
        job.status='ready'
        job.save()#update_fields=['status']
        
    return render(request,'inventory/inventory.html',context)

@login_required
def job_create(request):
    JobForm()
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
        form = JobForm(initial={'company':request.user.company})
    return render(request, 'inventory/job_create.html', {'form': form})
@login_required
def update_job(request, pk, cancel=0):
    
    job=Job.objects.filter(company=request.user.company).get(job_id=pk)
    items=JobItem.objects.filter(job=job)
    items_count=job.items.all().count()
    form = JobForm(instance=job,updating=True,)
    job_status=job.status
    comments_form=CommentForm(initial={
        'content_type': ContentType.objects.get_for_model(Job),
        'object_id': job.job_id,
        'company': request.user.company,
        })
    comments = Comment.objects.filter(content_type=ContentType.objects.get_for_model(Job), object_id=job.job_id,company=request.user.company)
      
    if cancel==1 :
            
            li=[]
            li=[item for item in job.items.all() if item.ordered and  item.arrived_quantity>0]
            if len(li)>0:
                request.session['job_post_data'] = request.POST
                return render(request,'inventory/confirm.html',{'items':li,'cancel_request':True,'job':job})
            messages.success(request,'Now you can cancel this job')
    if request.method=="POST":
        if 'yes_complete' in request.POST:
            post_data = request.session.pop('job_post_data', None)
            
            if post_data:
                form = JobForm(post_data, instance=job, updating=True)
                if form.is_valid():
                    form.save()
                    for item in job.items.all():
                        item.is_used=True
                        item.save(update_fields=['is_used'],dont_move_used=True)
                    
                    messages.success(request, "Job completed.")
                return render(request, 'inventory/job_update.html', {'form': form,'job':job,'comments_form':comments_form,'comments':comments,'items':items,'items_count':items_count})       
        post_data = request.session.pop('job_post_data', None) #in case of no retunr back
        if post_data and request.method == 'POST' and 'no_return_back' in request.POST :#---
            return redirect(f'update_job',pk=pk)
        if 'save' in request.POST:
            quotation = request.POST.get('quotation')
            if quotation:
                try:
                    # Try to convert to float (or int if you want only integers)
                    quotation = float(quotation)
                    if quotation <= 0:
                        raise ValueError("Quotation must be positive")
                except (TypeError, ValueError):
                    messages.error(request, "Quotation must be a valid positive number.")
                    # Optionally: re-render the form with errors and return
                    return render(request, 'inventory/job_update.html', {
                        'form': form,
                        'job': job,
                        'comments_form': comments_form,
                        'comments': comments,
                        'items': items,
                        'items_count': items_count
                    })
            else:
                quotation=job.quotation
            form = JobForm(request.POST, instance=job,updating=True)
           
            if form.is_valid() :
                if form.cleaned_data['status']=='completed':
                    li=[]
                    li=[item for item in job.items.all() if item.job_quantity != item.arrived_quantity]
                    if len(li)>0:
                        request.session['job_post_data'] = request.POST  # Save the POST data
                        return render(request,'inventory/confirm.html',{'items':li,'complete_request':True,'job':job})
                elif form.cleaned_data['status']=='cancelled'  :
                    
                    li=[]
                    li=[item for item in job.items.all() if item.ordered and  item.arrived_quantity>0 or item.from_warehouse]
                    if len(li)>0:
                        request.session['job_post_data'] = request.POST
                        return render(request,'inventory/confirm.html',{'items':li,'cancel_request':True,'job':job})
                try:
                    job.quotation=float(quotation) if float(quotation)>0 else None
                except:
                    pass
                form.save()
                form = JobForm(request.POST, instance=job,updating=True)
                messages.success(request, 'Job updated successfully')
                items=JobItem.objects.filter(job=job)
        comments_form=CommentForm(request.POST)
        if comments_form.is_valid() and 'add_comment' in request.POST: 
            comment = comments_form.save(commit=False)
            comment.added_by = request.user 
            comment.company = request.user.company
            comment.save()
            comments = Comment.objects.filter(content_type=ContentType.objects.get_for_model(Job), object_id=job.job_id,company=request.user.company)
            comments_form = CommentForm(initial={
            'content_type': ContentType.objects.get_for_model(Job),
            'object_id': job.job_id,
            'company': request.user.company,
            })
            form = JobForm(instance=job,updating=True)
        if 'send_email' in request.POST :
                if job.engineer is not None and job.status=="ready":
                    recipient_list=[]
                    recipient_list.append(job.engineer.email)
                    # parts=[]
                    # for part in job.items.all():
                    #     parts.append(part)
                    parts = [str(part) for part in job.items.all()]
                    parts_text = "\n".join(parts)
                    
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
                messages.error(request,"Failed")
                comments = Comment.objects.filter(content_type=ContentType.objects.get_for_model(Job), object_id=job.job_id,company=request.user.company)
                comments_form = CommentForm(initial={
                'content_type': ContentType.objects.get_for_model(Job),
                'object_id': job.job_id,
                'company': request.user.company,
                })
                form = JobForm(instance=job,)
                items=JobItem.objects.filter(job=job)
                return render(request, 'inventory/job_update.html', {'form': form,'job':job,'comments_form':comments_form,'comments':comments,'items':items,'items_count':items_count})       
    context={'form': form,'job':job,'comments_form':comments_form,'comments':comments,'items':items,'items_count':items_count,'job_status':job_status}
    return render(request, 'inventory/job_update.html', context)       
###########################-ITEM-######################
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
                                    # if JobItem.objects.filter(job=job,item=item.item,):
                                    #     jobitem=JobItem.objects.filter(job=job,item=item.item,).first()
                                    #     jobitem.job_quantity=jobitem.job_quantity+required_quantity
                                    #     jobitem.arrived_quantity=jobitem.job_quantity
                                    #     jobitem.save(update_fields=['job_quantity'])
                                    #     item.warehouse_quantity=item.warehouse_quantity-required_quantity
                                    #     item.save(update_fields=['warehouse_quantity'])
                                    #     if item.warehouse_quantity==0:
                                    #        # item.delete()
                                    #        print('deleting')
                                    # else: 
                                        JobItem.objects.create(
                                        job=job,
                                        from_warehouse=True, #if item.is_moved_from_job==None else False,
                                        item=item.item,
                                        arrived=True,
                                        job_quantity=+required_quantity,
                                        arrived_quantity=+required_quantity,
                                        was_for_job=item.is_moved_from_job if item.is_moved_from_job else None
                                        )
                                        item.warehouse_quantity=item.warehouse_quantity-required_quantity
                                       # item_save(item)
                                        item.save(update_fields=['warehouse_quantity'])#
                                        if item.warehouse_quantity==0:
                                            #item.delete()
                                            print('deleting2')
                                else:
                                    messages.error(request,"Not enough stock")
                                    form=ItemForm(job=job)
                                    stock_items_form=StokcItemsForm(company=request.user.company)
                                    return render(request, 'inventory/add_item.html', {'form': form,'job':job,'stock_items_form':stock_items_form})
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
                        ordered=form.cleaned_data['ordered']
                        reference=form.cleaned_data['reference']
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
                                                ordered=ordered,
                                                reference=reference,
                                                was_for_job=job,
                                                
                                                )
                            #item.job = job
                            #item.save()
                            form=ItemForm(job=job)
                            stock_items_form=StokcItemsForm(company=request.user.company)
                            messages.success(request, f'{item}-is added to job {job}')
                            
                            return render(request, 'inventory/add_item.html', {'form': form,'stock_items_form':stock_items_form,'job':job})
                        
                        elif pk is None and no_job: 
                            
                            item=form.save(commit=False)
                            
                            pn=form.cleaned_data['part_number']
                            try:
                                item_queryset = WarehouseItem.objects.get(item=Item.objects.get(Q(part_number=pn) & Q(company=request.user.company)))
                            except :
                                item_queryset=False
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
                                                        company=request.user.company,
                                                        )
                            messages.success(request, f'{item}-is added to warehouse')
                            return redirect('inventory')
                except IntegrityError:
                    messages.error(request, f'{item} — failed')
                # Raise an IntegrityError manually to roll back the transaction
                    #raise IntegrityError("Job does not exist, rolling back item save.")
                    
                    return render(request, 'inventory/add_item.html', {'form': form,'job':job,'stock_items_form':stock_items_form})
    stock_items_form=StokcItemsForm(company=request.user.company)
    return render(request, 'inventory/add_item.html', {'form': form,'job':job,'stock_items_form':stock_items_form})
@login_required
def update_item(request, pk):
    item = JobItem.objects.get(Q(id=pk) & Q(job__company=request.user.company))
    completed=item.job.status=='completed'
    form = JobItemForm(instance=item,)#,updating=True,completed=completed
    comments_form=CommentForm(initial={
        'content_type': ContentType.objects.get_for_model(JobItem),
        'object_id': item.id,
        'company': request.user.company,
        })
    comments= Comment.objects.filter(content_type=ContentType.objects.get_for_model(JobItem), object_id=item.id,company=request.user.company)
    if request.method == 'POST':
        
        comments_form=CommentForm(request.POST)
        if 'dont_move_used' in request.POST:
            next_url = request.POST.get('next')
            job_item = item
            
            if job_item.arrived_quantity>0:
                job_item.is_used=True
                job_item.job.status='cancelled'
                job_item.notes=''
                job_item.save(dont_move_used=True,update_fields=['is_used','notes'])
                job_item.job.save()#update_fields=['status']
                if next_url:
                    return redirect('inventory')
        elif 'yes_move' in request.POST:
            next_url = request.POST.get('next')
            
            try:
                job_item = item
                # Optional: Check if already used or empty
                if job_item.is_used or job_item.arrived_quantity == 0:
                    
                    messages.error(request, "Nothing to move or already used.")
                  
                try:
                    WarehouseItem.objects.get(Q(company=request.user.company) & Q(item=item.item))
                    create_new=False
                except:
                    create_new=True
                if not job_item.from_warehouse or create_new :
                    job=job_item.was_for_job if job_item.was_for_job else job
                    # Create WarehouseItem
                    WarehouseItem.objects.create(
                        item=job_item.item,
                        warehouse_quantity=job_item.arrived_quantity,
                        company=request.user.company,
                        
                        #is_used=job_item.is_used,
                        is_moved_from_job=job if job_item.was_for_job else None  ,   
                    )
                    
                else:
                
                    try:
                        wi=WarehouseItem.objects.get(Q(item=job_item.item) & Q(is_moved_from_job=True))
                    except:
                        
                        wi=WarehouseItem.objects.get(item=job_item.item)
                    wi.warehouse_quantity+=job_item.job_quantity
                    wi.save(update_fields=['warehouse_quantity'])
                # Delete JobItem after successful move
                job_item.job.status='cancelled'
                
                job_item.job.save()
                job_item.delete()
                messages.success(request,"Item moved to warehouse")
            except JobItem.DoesNotExist:
                messages.error(request,"Moving failed")
            if next_url:
                
                return redirect(next_url)
        
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
            return render(request,'inventory/confirm.html',{'item':item,'job_item':True})
        if 'yes_delete' in request.POST:
            try:
                with transaction.atomic():
                    item.delete()
                    messages.success(request,f'{item} deleted succssefully')
            except:
                messages.error(request,f'{item} deleting failed')
                return redirect(f'update_item',pk=pk)
            return redirect('inventory')
        elif 'no_return_back' in request.POST:
            return redirect(f'update_item',pk=pk)
        form = ItemForm(request.POST, request.FILES, instance=item,updating=True)
        if 'move_item' in request.POST :
            try:
                job_item = item

                # Optional: Check if already used or empty
                if job_item.is_used or job_item.arrived_quantity == 0:
                    
                    messages.error(request, "Nothing to move or already used.")
                    form = JobItemForm(instance=item,)
                    comments_form=CommentForm(initial={
                    'content_type': ContentType.objects.get_for_model(JobItem),
                    'object_id': item.id,
                    'company': request.user.company,
                    })
                    context = {'form': form,'item': item,'comments_form':comments_form,"comments":comments,'completed':completed}
                    return render(request, 'inventory/update_item.html', context)
                try:
                    WarehouseItem.objects.get(Q(company=request.user.company) & Q(item=item.item))
                    create_new=False
                except:
                    create_new=True
                if not job_item.from_warehouse or create_new :
                    job=job_item.was_for_job if job_item.was_for_job else job
                    # Create WarehouseItem
                    WarehouseItem.objects.create(
                        item=job_item.item,
                        warehouse_quantity=job_item.arrived_quantity,
                        reference=job_item.reference,
                        company=request.user.company,
                        
                        #is_used=job_item.is_used,
                        is_moved_from_job=job if job_item.was_for_job else None  ,   
                    )
                    
                else:
                
                    try:
                        wi=WarehouseItem.objects.get(Q(item=job_item.item) & Q(is_moved_from_job=True))
                    except:
                        
                        wi=WarehouseItem.objects.get(item=job_item.item)
                    wi.warehouse_quantity+=job_item.job_quantity
                    wi.save(update_fields=['warehouse_quantity'])
                # Delete JobItem after successful move
                job_item.delete()
                messages.success(request,"Item moved to warehouse")
            except JobItem.DoesNotExist:
                messages.error(request,"Moving failed")
            return redirect('inventory') 
        form = JobItemForm(request.POST, request.FILES, instance=item,)
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
                    item=form.save(commit=False)
                    item.save()
                    
                else:
                    witem=WarehouseItem.objects.get(item=item.item)
                    form = JobItemForm( instance=item,)
                    messages.error(request,f"Not enough stock, only {witem.warehouse_quantity} available")
                    context = {'form': form,'item': item,'comments_form':comments_form,"comments":comments}
                    return render(request, 'inventory/update_item.html', context)
            else:
                item=form.save(commit=False)
                item.save()
                

            form = JobItemForm( instance=item,)#request.POST, request.FILES,updating=True

            context = {'form': form,'item': item,'comments_form':comments_form,"comments":comments}
          
            return render(request, 'inventory/update_item.html', context)
    context = {'form': form,'item': item,'comments_form':comments_form,"comments":comments,"completed":completed}
    return render(request, 'inventory/update_item.html', context)
########################




@login_required
def update_warehouse_item(request, pk):
    print('ss')
    warehouse_item = WarehouseItem.objects.get(Q(company=request.user.company),Q(id=pk))
    
    item=warehouse_item.item
    #job=Job.objects.filter(company=request.user.company).get(job_id=item.job.job_id) if item.job else None
    #completed=job.status=='completed'
    form =WarehouseitemForm(instance=warehouse_item)#,updating=True
    # handler=WareohuseFormHandler(form,)
    # handler.set_form_fields(warehouse_item=warehouse_item)
    comments_form=CommentForm(initial={
        'content_type': ContentType.objects.get_for_model(WarehouseItem),
        'object_id': warehouse_item.id,
        'company': request.user.company,
        })
    comments= Comment.objects.filter(content_type=ContentType.objects.get_for_model(WarehouseItem), object_id=warehouse_item.id,company=request.user.company)
    if request.method == 'POST':
        
        print("OPOP")
        comments_form=CommentForm(request.POST)
        if comments_form.is_valid() and "just_add_comment" in request.POST :
            print("P")
            comment = comments_form.save(commit=False)
            comment.added_by = request.user 
            comment.company = request.user.company
            comment.save()

            comments= Comment.objects.filter(content_type=ContentType.objects.get_for_model(WarehouseItem), object_id=warehouse_item.id,company=request.user.company)

            comments_form=CommentForm(initial={
            'content_type': ContentType.objects.get_for_model(WarehouseItem),
            'object_id': warehouse_item.id,
            'company': request.user.company,
            })
            context = {'form': form,'item': item,'comments_form':comments_form,"comments":comments}
            return render(request, 'inventory/update_warehouse_item.html', context)
        if "delete" in request.POST:
            return render(request,'inventory/confirm.html',{'item':warehouse_item,'warehouse_item':True})
        
        if 'yes_delete' in request.POST:
            try:
                with transaction.atomic():
                    warehouse_item.delete()
                    messages.success(request,f'{warehouse_item} deleted succssefully')
            except:
                messages.error(request,f'{warehouse_item} deleting failed')
                return redirect(f'update_warehouse_item',pk=pk)
            return redirect('warehouse')
        elif 'no_return_back' in request.POST:
            return redirect(f'update_warehouse_item',pk=pk)
        form = WarehouseitemForm(request.POST, request.FILES, instance=warehouse_item,)
        # handler=WareohuseFormHandler(form,)
        # handler.set_form_fields()
        comments_form=CommentForm(request.POST)
        if form.is_valid() and 'edit' in request.POST: 
            # item=form.save(commit=False)
            # item.company=request.user.company
            # item.save(update_fields=['arrived_quantity','reference','name','price','supplier'],)#updating=True
            warehouse_quantity=form.cleaned_data['warehouse_quantity']
            warehouse_item.warehouse_quantity=warehouse_quantity
            warehouse_item.save(update_fields=['warehouse_quantity'])
            form = WarehouseitemForm( instance=warehouse_item,)
            messages.success(request,f'Item {warehouse_item} updated successfully')
            context = {'form': form,'warehouse_item': item,'comments_form':comments_form,"comments":comments}
            return render(request, 'inventory/update_warehouse_item.html', context)
    context = {'form': form,'item': item,'warehouse_item':warehouse_item,'comments_form':comments_form,"comments":comments}
    return render(request, 'inventory/update_warehouse_item.html', context)
    
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
            
            context = {
                
                'users': CustomUser.objects.filter(company=request.user.company),
                'engineers':Engineer.objects.filter(company=request.user.company)
            }
            return render(request, 'inventory/admin_panel.html',context )
        else:
            return HttpResponse("You are not authorized to view this page")
@owner_only
def update_user(request, pk):
    worker=CustomUser.objects.get(Q(company=request.user.company) & Q(pk=pk))
    form=registerworker(instance=worker,editing=True)
    if request.method=='POST':
        form=registerworker(request.POST,instance=worker,editing=True)
        if form.is_valid():
            form.save()
            messages.success(request,'User updated successfully')
            form=registerworker(instance=worker,editing=True)
            return render(request, 'inventory/update_user.html',{'form':form})
    
    return render(request, 'inventory/update_user.html',{'form':form})


def register_company(request):
    """ Register a new company and its admin user """
    company_form = companyregisterForm(user=request.user,)
    user_form = registerForm()

    if request.method == 'POST':
        company_form = companyregisterForm(request.POST,)
        user_form = registerForm(request.POST,)
        if company_form.is_valid() and user_form.is_valid():
            with transaction.atomic():
                
                
                user = user_form.save(commit=False)
                user.set_password(user_form.cleaned_data['password'])
                user.is_owner=True
                user.save()

                # Step 2: Now save the company and assign the owner
                company = company_form.save(commit=False)
                company.owner = user
                company.save()

                # Step 3: Update user with the company
                user.company = company
                user.save()

            # Step 3: Assign the user to the "Admin" group
            

                messages.success(request, 'Company was created successfully! Now you can login.')
           # return redirect('login')
        else:
            messages.warning(request, f"Registration failed.")
    # else:
    #     company_form = companyregisterForm(user=request.user,initial={'group': "owner"})
    #     user_form = registerForm(request.POST,registering=True)

    return render(request, 'auths/register_company.html', {'company_form': company_form, 'user_form': user_form})
#############
def warehouse(request):
    warehouse_items=WarehouseItem.objects.filter(company=request.user.company,is_moved_from_job=None)
    moved_items=WarehouseItem.objects.filter(is_moved_from_job__isnull=False ,company=request.user.company , warehouse_quantity__gt=0)
    used_warehouse_items=JobItem.objects.filter(job__company=request.user.company,is_used=True,from_warehouse=True)
    used_moved_items=JobItem.objects.filter(job__company=request.user.company,is_used=True,was_for_job__isnull=False)
    return render(request,'inventory/warehouse.html',{'warehouse_items':warehouse_items,'moved_items':moved_items,'used_warehouse_items':used_warehouse_items,'used_moved_items':used_moved_items})

def engineer(request):
    form=EngineerForm()
    if request.method=="POST":
       form=EngineerForm(request.POST)
       if form.is_valid:
            eng=form.save(commit=False)
            try:
                Engineer.objects.get(Q(name=eng.name) & Q(company=request.user.company))
                ex=True
            except Engineer.DoesNotExist:
                ex=False
            if not ex:
                eng.company=request.user.company
                eng.save()
                messages.success(request,f"Engineer {eng.name} is added")
            else:
                messages.error(request,"Engineer with the same name exists")
            return render(request,'inventory/eng.html',{'form':form})
    return render(request,'inventory/eng.html',{'form':form})

def create_batch_items(request):
    if request.method == 'POST':
        item_data = {
            'name': request.POST['name'],
            'part_number': request.POST['part_number'],
            'reference': request.POST['reference'],
            'price': float(request.POST['price']) ,
            'supplier': request.POST['supplier'],
            'arrived_quantity': int(request.POST['arrived_quantity']),
            'company':request.user.company
        }
        # Save to database
        item=Item.objects.create(**item_data)

        try:
            
            exist=WarehouseItem.objects.get(item__part_number=item.part_number)
            
        except WarehouseItem.DoesNotExist:
            exist=False
        if exist:
            wi=WarehouseItem.objects.get(item__part_number=item.part_number)
            wi.warehouse_quantity+=item.arrived_quantity
            wi.save(update_fields=['warehouse_quantity'])

        else:
            WarehouseItem.objects.create(item=item,warehouse_quantity=item.arrived_quantity,company=request.user.company,reference=item.reference)
        messages.success(request,f'{item.arrived_quantity} of {item.name} added to the warehouse')
        # Remove this item from session
        items = request.session.get('batch_items', [])
        items = [item for item in items if item['part_number'] != item_data['part_number']]
        request.session['batch_items'] = items
        return redirect('batch_entry')

import pandas as pd
def batch_entry(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        df = pd.read_excel(excel_file)
        data = df.to_dict(orient='records')

        # Save all items in session
        request.session['batch_items'] = data
        return redirect('batch_entry')  # refresh the page

    # Load current items from session
    data = request.session.get('batch_items', [])
    return render(request, 'inventory/batch_entry.html', {'data': data})
def clear_batch(request):
    request.session['batch_items'] =[]
    return redirect('batch_entry')
import requests
from django.shortcuts import render

def fetch_api_data(request):
    url = "https://jsonplaceholder.typicode.com/posts"
    response = requests.get(url)
    data = response.json()  # Convert to dict

    return render(request, 'inventory/api_data.html',{'data':data})

def fetch_jobs(request):
    url = "https://8dea2507-abbb-44c8-8ca4-ac142d8f9edb.mock.pstmn.io/jobs"
    data=response = requests.get(url)
    data = response.json()  
    #data = data.get("items", [])# Convert to dict
    
    return render(request, 'inventory/sf.html', {'data': data})

#youssif_USF_SPY
