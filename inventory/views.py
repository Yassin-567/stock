from django.shortcuts import render,redirect,HttpResponse, get_object_or_404
from .models import CustomUser,Company,Job,Item,Comment,JobItem,WarehouseItem,Engineer,category,CompanySettings
from .forms import ItemForm,SearchForm,registerForm,loginForm,companyregisterForm,JobForm,CommentForm,JobItemForm,WarehouseitemForm,EngineerForm,registerworker,CategoriesForm,CompanySettingsForm,ForgotPasswordForm
from django.contrib.auth import authenticate, login, logout , update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .decorators import admins_only,no_ban,owner_only
from django.db.models import F
from django.db.models import Count, Q

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from django.core.mail import send_mail
from django.core.paginator import Paginator
from .myfunc import generate_otp,send_otp_email
from django.contrib.auth.hashers import make_password
import time
#import requests


# from django.core.mail import send_mail
# def guest(request):
#     random_id = uuid.uuid4().hex[:8]
#     username = f"guest_{random_id}"
#     email = f"{username}@example.com"
#     first_names = ["Alex", "Sam", "Jamie", "Taylor", "Jordan"]
#     last_names = ["Smith", "Brown", "Lee", "Clark", "Davis"]


@login_required(login_url='login', redirect_field_name='inventory')
def logout_user(request):
    if not request.user.is_authenticated:
        messages.error(request, 'You are not logged in.')
        return redirect('login')
    logout(request)
    return redirect('login')
def forgot_password(request):
    form=ForgotPasswordForm()
    if request.method=='POST' and 'confirm_new_password' in request.POST:
        email=request.session['register_email']
        user=CustomUser.objects.get(email=email)
        form=registerworker(request.POST,instance=user,enable_edit=True,updating=True,changing_password=True)
        
        if form.is_valid():
            new_password=form.cleaned_data['password']
            user.set_password(new_password)
            user.save(update_fields=['password'])
            for k in ['register_email','password_otp','verifying','allow_password_change','otp_generated_at']:
            
                request.session.pop(k,None)
              
            form=registerworker(instance=user,enable_edit=False,updating=True,)

            messages.success(request,'Password changed successfully')    
            return redirect('login')
    if request.method=='POST' and 'send_otp' in request.POST:
        form=ForgotPasswordForm(request.POST)
        if form.is_valid():
            email=form.cleaned_data['email']
            otp=generate_otp()
            request.session['otp_generated_at']=time.time()
            request.session['register_email']=email
            request.session['password_otp']=otp
            request.session['verifying'] ="forgot_password"
            send_otp_email(email,otp)
            return redirect(verify_otp)
    try:
        allow_password_change=request.session['allow_password_change'] 
    except:
        allow_password_change=False
    if allow_password_change :
        print(allow_password_change)
        email=request.session['register_email']
        user=CustomUser.objects.get(email=email)
        form=registerworker(instance=user,enable_edit=True,updating=True,changing_password=True)
        
        for k in['allow_password_change','password_otp']:
            request.session.pop(k,None)
        return render(request, 'inventory/update_user.html',{'form':form,'editing':True,'changing_password':True})

    return render(request,'auths/forgot_password.html',{'form':form})

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
    
        # rjobs = Job.objects.annotate(item_count=Count('items')).filter(items_arrived=True).prefetch_related('items')
    rjobs=Job.objects.filter(company=request.user.company)
    status = request.GET.get('status')
    
    try:
        if status  :
            request.session['status'] = status
            rjobs = rjobs.filter(status=status) if status!='' else rjobs
        
        elif request.session['status'] :
            status=request.session.pop('status', None)
            rjobs = rjobs.filter(status=status) if status!='' else rjobs
    except:
        pass
   
    paginator=Paginator(rjobs,10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context={
            'jobs_count':rjobs,
            'rjobs': page_obj,
            'page_obj':page_obj,
            'status':status,
            }
    if request.method=='POST' and "reset_notes" in request.POST:
        jobitem=JobItem.objects.get(id=pk)
        # item=Item.objects.get(id=jobitem.item.id)
        jobitem.notes=None
        jobitem.is_used=False
        jobitem.save(update_fields=['is_used','notes'])
        jobitem.job.save(update_fields=['status','items_arrived'])
        print("STAT",status)
        return render(request,'inventory/inventory.html',{
            
            'rjobs': page_obj,
            'page_obj':page_obj,
            'status':'paused',

            })
    elif request.method=="POST" and 'job_is_ready' in request.POST:
        job=Job.objects.get(job_id=pk,company=request.user.company)
        if job.items.exclude(is_used=False).exists():
            messages.error(request,'There is a used item')
            return render(request,'inventory/inventory.html',context)
        job.status='ready'
        job.save()#update_fields=['status']
    if 'coming_from_job' in request.POST:
        print("Yes")
        return redirect('update_job', jobitem.job.job_id)
    else:
        return render(request,'inventory/inventory.html',context)
def add_category(request):
    form=CategoriesForm()
    if request.method=='POST':
        form=CategoriesForm(request.POST)
        if form.is_valid():
            cat=form.save(commit=False)
            cat.company=request.user.company
            try:
                exist_cat=category.objects.get(category__icontains=cat.category)
                messages.error(request,f'A similar category exists: <span class="cat-highlight" style="color: rgb(230, 15, 15);">{exist_cat}</span>')
            except:
                form.save()
                messages.success(request,f'Added <span class="cat-highlight" style="color: rgb(145, 34, 230);">{cat}</span> category successfully')
                   
           
    return render(request,'inventory/add_cat.html',{"form":form})
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
    print(cancel)
    if cancel==1 :
            print(00000)
            li=[]
            li=[item for item in job.items.all() if (item.ordered or item.from_warehouse) and  item.arrived_quantity>0 and item.is_used==False ]
            for i in li:
                print('pp')
                print(i,i.ordered,i.is_used)
            if len(li)>0:
                request.session['job_post_data'] = request.POST
                return render(request,'inventory/confirm.html',{'items':li,'cancel_request':True,'job':job})
            job.status='cancelled'
            job.save(update_fields=['status'])
            messages.success(request,'Now this job is cancelled')
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
                    
                    print("O")
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
                    li=[item for item in job.items.all() if (item.ordered or item.from_warehouse ) and  item.arrived_quantity>0 and not item.is_used ]
                    if len(li)>0:
                        request.session['job_post_data'] = request.POST
                        return render(request,'inventory/confirm.html',{'items':li,'cancel_request':True,'job':job})
                try:
                    job.quotation=float(quotation) if float(quotation)>0 else None
                    job.quoted=True
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
    warehouse_items=WarehouseItem.objects.filter(company=request.user.company,warehouse_quantity__gt=0)
    #stock_items_form=StokcItemsForm(company=request.user.company)
    #form.fields['job'].widget = MultipleHiddenInput() 
    # if job is None:
    #     form.fields['job_quantity'].widget = HiddenInput()
    # else:
    #     form.fields['job_quantity'].widget = forms.TextInput()
    if request.method=='POST':
        
        if 'reset_search' in request.POST:
            if pk is not None :
                
                warehouse_items=WarehouseItem.objects.filter(company=request.user.company,warehouse_quantity__gt=0,)
                return render(request, 'inventory/add_item.html', {'form': form,'job':job,'warehouse_items':warehouse_items,'show_stock':True})

        if 'searching_warehouse' in request.POST:
            if pk is not None :
                query = request.POST.get('search_query')
                if len(query)>0 and not 'reset_search' in request.POST:
                    warehouse_items=WarehouseItem.objects.filter(company=request.user.company,warehouse_quantity__gt=0,item__part_number__iexact=query)
                return render(request, 'inventory/add_item.html', {'form': form,'job':job,'warehouse_items':warehouse_items,'query':query,'show_stock':True})

        if 'adding_from_stock' in request.POST:
            
            form=ItemForm(request.POST,)
            item_id = request.POST.get('selected_item_id')
            
            required_quantity = int(request.POST.get('required_quantity'))
            item=WarehouseItem.objects.get(Q(company=request.user.company),Q(id=item_id))
            
            try:
                with transaction.atomic():
                    if required_quantity<=0:
                        messages.error(request,"Quantity must be positive integer")
                        form=ItemForm(job=job)
                        warehouse_items=warehouse_items
                        return render(request, 'inventory/add_item.html', {'form': form,'job':job,'warehouse_items':warehouse_items})
        
                    if item.warehouse_quantity>0 and item.warehouse_quantity>= required_quantity:
                       
                            JobItem.objects.create(
                            job=job,
                            from_warehouse=True, #if item.is_moved_from_job==None else False,
                            item=item.item,
                            arrived=True,
                            job_quantity=+required_quantity,
                            arrived_quantity=+required_quantity,
                            category=item.category,
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
                        warehouse_items=warehouse_items
                        return render(request, 'inventory/add_item.html', {'form': form,'job':job,'warehouse_items':warehouse_items,'show_stock':True})
            except IntegrityError:
                messages.error(request,"Failed")
            
            messages.success(request, 'Item added from stock successfully')
            form=ItemForm(job=job)
            warehouse_items=warehouse_items
            return render(request, 'inventory/add_item.html', {'form': form,'job':job,'warehouse_items':warehouse_items,'show_stock':True})
        elif 'adding_new' in request.POST:
            form=ItemForm(request.POST)
            
            if form.is_valid():
                print(5556)
                try:
                    with transaction.atomic():
                        
                        
                        job_quantity=form.cleaned_data['required_quantity']
                        arrived_quantity=form.cleaned_data['arrived_quantity']
                        ordered=form.cleaned_data['ordered']
                        reference=form.cleaned_data['reference']
                        category=form.cleaned_data['category']
                        if pk is not None:
                            print("KJKJK")
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
                                                category=category
                                                )
                            #item.job = job
                            #item.save()
                            form=ItemForm(job=job)
                            warehouse_items=warehouse_items
                            messages.success(request, f'{item}-is added to job {job}')
                            
                            return render(request, 'inventory/add_item.html', {'form': form,'warehouse_items':warehouse_items,'job':job})
                        
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
                                                        category=item.category
                                                        )
                            messages.success(request, f'{item}-is added to warehouse')
                            return redirect('inventory')
                except IntegrityError:
                    messages.error(request, f'{item} — failed')
                # Raise an IntegrityError manually to roll back the transaction
                    #raise IntegrityError("Job does not exist, rolling back item save.")
                    
                    return render(request, 'inventory/add_item.html', {'form': form,'job':job,'warehouse_items':warehouse_items})
    warehouse_items=warehouse_items
    return render(request, 'inventory/add_item.html', {'form': form,'job':job,'warehouse_items':warehouse_items})
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
            print(next_url)
            job_item = item
            
            if job_item.arrived_quantity>0:
                job_item.is_used=True
                # job_item.job.status='cancelled'
                job_item.notes=''
                job_item.save(dont_move_used=True,update_fields=['is_used','notes'])
                job_item.job.save()#update_fields=['status']
                if next_url:
                    return redirect(next_url)
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
                        category=job_item.category,
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
                        category=job_item.category,
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
            warehouse_item.save(update_fields=['warehouse_quantity','category'])
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
        company_email=company.company_email
        form = companyregisterForm(request.POST ,request.FILES, instance=company,user=request.user,enable_edit=False)
        if form.is_valid():
            
            email=form.cleaned_data['company_email']
            # if email!=company_email:
            request.session['verifying']="updating_company"
            request.session['company_name'] = form.cleaned_data['company_name']
            request.session['company_email'] = email
            request.session['address'] = form.cleaned_data['address']
            request.session['phone'] = form.cleaned_data['phone']
            
            otp=generate_otp()
            request.session['otp_generated_at']=time.time()

            request.session['company_updating_otp']=otp
            send_otp_email(email,otp)
            return redirect('otp')
            # else:
            #     form.save()
                
            # form = companyregisterForm(instance=company,user=request.user,updating=True,enable_edit=False)
            # context = {'form': form,'company': company,'enable_edit':False}
            # messages.success(request,"Company updated successfuly")
            # return render(request, 'inventory/update_company.html',context)
    
    
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
# @owner_only
def update_user(request, pk):
    worker=CustomUser.objects.get(Q(company=request.user.company) & Q(pk=pk))
    form=registerworker(instance=worker,enable_edit=False,updating=True)
    if request.method=='POST' and 'change_password' in request.POST:
        form=registerworker(instance=worker,enable_edit=True,updating=True,changing_password=True)

        return render(request, 'inventory/update_user.html',{'form':form,'editing':True,'changing_password':True})
    if request.method=='POST' and 'confirm_new_password' in request.POST:
        form=registerworker(request.POST,instance=worker,enable_edit=True,updating=True,changing_password=True)
        
        if form.is_valid():
            print('fa')
            form.save()
            form=registerworker(instance=worker,enable_edit=False,updating=True,)
            messages.success(request,'Password changed successfully')
        return render(request, 'inventory/update_user.html',{'form':form,'editing':False,'changing_password':False})
    if request.method=='POST' and 'edit' in request.POST:

        form=registerworker(instance=worker,enable_edit=True,updating=True,)
        return render(request, 'inventory/update_user.html',{'form':form,'editing':True})
    if request.method=='POST' and 'update' in request.POST:
        form=registerworker(request.POST,instance=worker,enable_edit=True,updating=True,)
        if form.is_valid():
            
            email=form.cleaned_data['email']
            if email!=request.user.email:
                request.session['verifying']="updating_user"
                request.session['username'] = form.cleaned_data['username']
                request.session['register_email'] = email
                
                otp=generate_otp()
                request.session['otp_generated_at']=time.time()
                request.session['user_updating_otp']=otp
                send_otp_email(email,otp)
                return redirect('otp')
            else:
                form.save()
                messages.success(request,'User updated successfully')
            
            
            form=registerworker(instance=worker,enable_edit=False,updating=True,)
            return render(request, 'inventory/update_user.html',{'form':form})
    return render(request, 'inventory/update_user.html',{'form':form,'editing':False})


def register_company(request):
    """ Register a new company and its admin user """
    company_form = companyregisterForm(user=request.user,)
    user_form = registerForm()
    if request.method == 'POST' and 'signup':
        company_form = companyregisterForm(request.POST)
        user_form = registerForm(request.POST)

        if company_form.is_valid() and user_form.is_valid():
            email = user_form.cleaned_data.get('email')  
            company_email = company_form.cleaned_data.get('company_email') 
            email_otp = generate_otp()
            if email==company_email:
                company_otp=email_otp
            else:
                company_otp = generate_otp()
            request.session['otp_generated_at']=time.time()
            request.session['verifying'] = "registering_company"    
            request.session['register_email'] = email
            request.session['company_email'] = company_email
           
            request.session['email_otp'] = email_otp
            request.session['company_otp'] = company_otp

            request.session['company_data'] = company_form.cleaned_data
            request.session['user_data'] = user_form.cleaned_data
            try:
                send_otp_email(email, email_otp)
                send_otp_email(company_email, company_otp)
                messages.success(request,'''Check your email & company's email for OTPs''')
                return redirect('otp')
            except:
                messages.error(request,'Failed to send OTP')


    

    return render(request, 'auths/register_company.html', {'company_form': company_form, 'user_form': user_form})

#############
def verify_otp(request) :
    
    email=request.session.get('register_email')
    company_email=request.session.get('company_email')
    otp_generated_at = request.session.get('otp_generated_at')
    otp_expiry_seconds = 300 # 5 minutes
    print(otp_generated_at,otp_expiry_seconds,)
    print(email,company_email,)
    print(request.session.get('verifying'))

    if request.method=='POST' and 'resend_otp' in request.POST:
        verifying=request.session.get('verifying')
        if verifying=='forgot_password':
        
            otp=generate_otp()
            request.session['otp_generated_at']=time.time()
            request.session['password_otp']=otp
            request.session['verifying'] ="forgot_password"
            try:
                send_otp_email(email,otp)
            except:
                messages.error(request,"Failed to resened OTP, go back and try again")
        elif verifying=='updating_user':
            otp=generate_otp()
            request.session['otp_generated_at']=time.time()

            request.session['user_updating_otp']=otp
            send_otp_email(email,otp)
        elif verifying=='updating_company':
            request.session['company_email'] = email
            
            otp=generate_otp()
            request.session['otp_generated_at']=time.time()
            request.session['company_updating_otp']=otp
            send_otp_email(email,otp)
        left_time = otp_expiry_seconds - (time.time() - otp_generated_at) 
        left_time=left_time if left_time>0 else "Expired"
    if request.method == 'POST' and 'forgot_password' in request.POST:
        input_user_otp=request.POST.get('email_otp')
        user_session_otp = request.session.get('password_otp')
        
        print('uiuiuiui',user_session_otp,input_user_otp)
        if (
            input_user_otp == user_session_otp and
            otp_generated_at is not None and
            (time.time() - otp_generated_at <= otp_expiry_seconds)
        ):
            
            request.session['allow_password_change']=True
            
            return redirect('forgot_password')
        else:
            messages.error(request,"Wrong OTP, Try agian.")
    if request.method == 'POST' and 'updating_user' in request.POST:
        input_user_otp=request.POST.get('email_otp')
        user_session_otp = request.session.get('user_updating_otp')
        
        print('ppp',user_session_otp,input_user_otp)
        if (
            input_user_otp == user_session_otp and
            otp_generated_at is not None and
            (time.time() - otp_generated_at <= otp_expiry_seconds)
        ):
            username = request.session.get('username')
            user=CustomUser.objects.get(id=request.user.id)
            user.email=email
            user.username=username
            user.save(update_fields=['username','email',])
            for k in ['username','register_email','otp_generated_at']:
                request.session.pop(k,None)
            messages.success(request,"User updated successfully")
            return redirect('update_user',request.user.id)
        else:
            messages.error(request,"Wrong OTP, Try agian.")
    if request.method == 'POST' and 'updating_company' in request.POST:
        input_company_otp=request.POST.get('company_otp')
        company_session_otp = request.session.get('company_updating_otp')
        print(company_session_otp)
        if (
                    input_company_otp==company_session_otp and
                    otp_generated_at is not None and
                    (time.time() - otp_generated_at <= otp_expiry_seconds)
                ):
            company_name = request.session.get('company_name')
            phone = request.session.get('phone')
            address = request.session.get('address')

            company=Company.objects.get(id=request.user.company.id)
            company.company_name=company_name
            company.company_email=company_email
            company.address=address
            company.phone=phone
            company.save(update_fields=['company_name','company_email','address','phone'])
            for k in ['company_email','company_name','phone','address','otp_generated_at']:
                request.session.pop(k,None)
            messages.success(request,"Company updated successfully")
            return redirect('update_company')
        else:
            messages.error(request,"Wrong OTP, Try agian.")
    if request.method == 'POST' and 'registering_company' in request.POST:
        input_company_otp=request.POST.get('company_otp')
        input_email_otp=request.POST.get('email_otp')
        
        company_session_otp = request.session.get('company_otp')
        email_session_otp = request.session.get('email_otp')
        
        if (
                    input_user_otp == user_session_otp and
                    input_email_otp==email_session_otp and
                    otp_generated_at is not None and
                    (time.time() - otp_generated_at <= otp_expiry_seconds)
                ):
            
            with transaction.atomic():
                try:
                    company_data = request.session.get('company_data')
                    user_data = request.session.get('user_data').copy()  # Make a copy so we can modify safely
                    user_data.pop('password2', None)  # Remove password2 if it exists
                    
                    user_data['password'] = make_password(user_data['password'])
                    company = Company.objects.create(**company_data)
                    user = CustomUser.objects.create(company=company, **user_data)
                    user.is_owner=True
                    company.owner=user
                    company.save(update_fields=['owner'])
                    user.save(update_fields=['is_owner'])
                    # Optionally log the user in
                    request.session.flush()

                    messages.success(request,'Company created successfully')
                    return redirect('login')
                except:
                    messages.error(request,'Failed creating company. Try again')
        else:
            messages.error(request,"Wrong OTP. Try again")
    left_time = otp_expiry_seconds - (time.time() - otp_generated_at) 
    left_time=left_time if left_time>0 else "Expired"
    return render(request, 'auths/otp.html', {'email':email,'company_email':company_email,'left_time':left_time})
@owner_only

def company_settings(request):
    # from inventory.utils import  seed_company_and_users   
    company = request.user.company
    print(company)

    try:
        instance = company.settings
    except CompanySettings.DoesNotExist:
        instance = None

    form = CompanySettingsForm(request.POST or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        settings = form.save(commit=False)
        settings.company = company
        settings.save()
        
        # from inventory.utils import migrate_client_db, seed_company_and_users
        # migrate_client_db(settings) 
        # from inventory.utils import migrate_client_db, seed_company_and_users
        
        #     # 2. Migrate the new DB
        # migrate_client_db(settings)  # only runs `call_command('migrate')`

        # # 3. Now that tables exist, copy company and user
        # seed_company_and_users(settings)

    return render(request, 'inventory/company_settings.html', {'form': form})
def warehouse(request):
    from django.db.models import Sum
    parts_summary = (
        WarehouseItem.objects
        .filter(company=request.user.company)
        .values('item__part_number', 'item__name', 'category__category')  # updated line
        .annotate(total_quantity=Sum('warehouse_quantity'))
        .order_by('item__part_number')
    )

    print(parts_summary)
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
def search_view(request):
    form=SearchForm()
    return render(request,'inventory/inventory.html',{'form':form})
def create_batch_items(request):
    if request.method == 'POST':
        cat_val = request.POST.get('category')
        print("VAL",cat_val)
        if cat_val:
            try:
                cat_obj = category.objects.get(category__icontains=cat_val)
                messages.error(request,f'exist similar {cat_obj}')
                print("1")
            except category.DoesNotExist:
                # fallback to Others if not found
                cat_obj, _ = category.objects.get_or_create(company=request.user.company, category=cat_val)
                print('2')
        else:
            cat_obj, _ = category.objects.get_or_create(company=request.user.company, category='Others')
            
        item_data = {
            'name': request.POST['name'],
            'part_number': request.POST['part_number'],
            'reference': request.POST['reference'],
            'price': float(request.POST['price']) ,
            'supplier': request.POST['supplier'],
            'arrived_quantity': int(request.POST['arrived_quantity']),
            'company':request.user.company,
            'category': cat_obj,
        }
        
        # Save to database
        item=Item.objects.create(**item_data)

        try:
            
            exist=WarehouseItem.objects.get(item__part_number=item.part_number )
            
        except WarehouseItem.DoesNotExist:
            exist=False
        if exist:
            wi=WarehouseItem.objects.get(item__part_number=item.part_number)
            wi.warehouse_quantity+=item.arrived_quantity
            wi.save(update_fields=['warehouse_quantity'])

        else:
            WarehouseItem.objects.create(item=item,warehouse_quantity=item.arrived_quantity,company=request.user.company,reference=item.reference,category=item.category)
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
