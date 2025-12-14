from django.shortcuts import render,redirect,HttpResponse, get_object_or_404
from .models import CustomUser,Company,Job,Comment,JobItem,WarehouseItem,Engineer,Category,CompanySettings,Email,History,SchedulerGroup
from .forms import SearchForm,registerForm,loginForm,companyregisterForm,JobForm,CommentForm,JobItemForm,WarehouseitemForm,EngineerForm,registerworker,CategoriesForm,CompanySettingsForm,ForgotPasswordForm,GuestEmail
from django.contrib.auth import authenticate, login, logout , update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .decorators import admins_only,no_ban,owner_only
from django.db.models import Count, Q,Case, When, BooleanField, Value,F,Sum
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from django.core.mail import send_mail
from django.core.paginator import Paginator
from .myfunc import generate_otp,send_otp_email,send_multiple_emails, send_guest_email,update_if_changed,sync_engineers_func,haversine,get_coords,get_drive_time_ors,optimize_group_order,optimize_group_order2,_greedy_fallback,move,refresh_sf_token , remove_job_from_group,i_donot_work_on_this,i_work_on_this
from django.contrib.auth.hashers import make_password
import time
from django.conf import settings
from datetime import datetime
from django.utils.crypto import get_random_string
import random
from urllib.parse import urlencode
import requests
from django.utils.dateparse import parse_date, parse_time
from django.forms.models import model_to_dict

def create_guest_request(request):
    form=GuestEmail()
    guest_id = request.COOKIES.get("guest_id")
    if guest_id:
        messages.error(request,'You already have a guest account!!!')
        return redirect('login')
    if request.method == "POST":
        choice = request.POST.get("choice")
        try:
            if choice=='yes':
                
                form=GuestEmail(request.POST)
                if form.is_valid():
                    return create_guest_account(request,email=form.cleaned_data['email'])
            else:
                return redirect('login')
        except:
            messages.error(request,'Oops, something is not quite right.\n Try again in a minute')
            return redirect(create_guest_request)
    return render(request,'auths/confirm.html',{'form':form})

def create_guest_account(request,email):
    print(email)
    
    # Create guest company
    company = Company(
        company_name="Guest-" + get_random_string(6),
        company_email=f"guest{get_random_string(6)}@example.com",
        address=get_random_string(6),
        phone=random.randint(100000, 999999),
        is_guest=True,
    )
    raw_password=get_random_string(12)
    # Create guest user
    user = CustomUser(
        email=f"guest{get_random_string(8)}@example.com",
        password=raw_password ,
        username="guest_" + get_random_string(6),
        company=company,
        permission="owner"
    )
    user.set_password(user.password)

    # Make user the owner (optional, depends on your business logic)
    company.save(request=request,dont_save_history=True)
    user.save(request=request,dont_save_history=True)
    company.owner = user
    
    company.save(request=request,dont_save_history=True)
    user.is_owner=True
    user.save(request=request,dont_save_history=True)
    send_guest_email(email=email,login_email=user.email,password=raw_password)
    messages.success(request,f'Your guest account has been created. \n Check your email to login')
    response = redirect("inventory")

    response.set_cookie("guest_id", company.id, max_age=7*24*60*60)
    return response


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
            user.save(update_fields=['password'],)
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
    
    if request.method == 'POST' :
        form=loginForm(request.POST)
        email=request.POST['email']
        password=request.POST['password']
        user = authenticate(email=email, password=password)
        print(user)
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
            user = form.save(commit=False) 
            user.set_password(form.cleaned_data['password'])  
            company = Company.objects.get(id=request.user.company.id)
            user.company = company
            
            user.save(request=request)  
            
            messages.success(request, 'You have successfully registered a new user')
            return redirect('register') 
        else: 
            form = registerworker()
            messages.error(request, "Registration failed. Please check the form.")
    else:
        form = registerworker()
    return render(request, 'auths/register.html', {'form': form})

@login_required(login_url='login', redirect_field_name='inventory')
@no_ban
def inventory(request,pk=None):
    now_time=timezone.now()
    rjobs=Job.objects.filter(company=request.user.company).order_by('retirement_date')
    refresh=True if request.GET.get("refresh") else False
    sort=request.GET.get("sort",None)
    
    if 'view_option' in request.GET:
            # Save new choice in session
            request.session['view_option'] = request.GET.get('view_option')

        # Step 2: Get current option from session (or set default)
    view_option = request.session.get('view_option', 'detailed_view')

    if refresh:
        status = None
        date = None
        q=None
        quotation_status=None
        age=None
        added_from_date=None
        added_to_date=None
        
    else:
        status = request.GET.get('status')
        q=request.GET.get('q')
        q=q.strip() if q else None
        date = request.GET.get('date')
        status = status.strip() if status else None
        date = date.strip() if date else None
        
        added_to_date = request.GET.get('added_to_date')
        added_from_date = request.GET.get('added_from_date')
        quotation_status = request.GET.get('quotation_status') 
        age = request.GET.get('age') if request.GET.get('age') else None

        # if status is not None:
        #     request.session['status'] = status
        # elif request.session.get('status') is not None:
        #     status = request.session['status']
        if status and status != 'all':
            if status == 'on_hold':
                rjobs = rjobs.filter(on_hold=True)
            elif status == "quoted":
                rjobs = rjobs.filter(quoted=True)
            elif status == "parts_need_attention":
                rjobs = rjobs.filter(parts_need_attention=True)
            else:
                rjobs = rjobs.filter(status=status)
            
        if date:
            rjobs = rjobs.filter(date=date)  
        if q:
           
            job_id_filter = Q()
            try:
                # Try to convert q to int for job_id search
                job_id_int = int(q)
                job_id_filter = Q(job_id=job_id_int)
            except (ValueError, TypeError):
                pass
            rjobs = rjobs.filter(
                job_id_filter |
                Q(parent_account__icontains=q) |
                Q(address__icontains=q) 
                # Add more fields as needed
            )
        
        if added_to_date or added_from_date:
            if added_from_date and added_to_date:
                if added_from_date > added_to_date:
                    messages.error(request, "The 'From' date cannot be later than the 'To' date.")
                    if view_option == "compact_view":
                        return redirect('inventory_compact')
                    else:
                        return redirect('inventory')
                # elif added_from_date == added_to_date:
                #     rjobs = rjobs.filter(birthday=added_to_date_obj)
            if added_from_date:
                added_from_date_obj = datetime.strptime(added_from_date, '%Y-%m-%d').date()
                rjobs = rjobs.filter(birthday__date__gte=added_from_date_obj)
            if added_to_date:
                added_to_date_obj = datetime.strptime(added_to_date, '%Y-%m-%d').date()
                rjobs = rjobs.filter(birthday__date__lte=added_to_date_obj)
        if age:
            if age == 'new':
                rjobs = rjobs.filter(retirement_date__gte=now_time )
            elif age == 'old':
                rjobs = rjobs.filter(retirement_date__lt=now_time )
        if quotation_status:
            if quotation_status == 'accepted':
                rjobs = rjobs.filter(quote_accepted=True)
            elif quotation_status == 'declined':
                rjobs = rjobs.filter(quote_declined=True)
            elif quotation_status == 'waiting':
                rjobs = rjobs.filter(quoted=True, quote_accepted=False, quote_declined=False)
            else:
                quotation_status = None
    if sort and sort!="quotation" and sort!="-quotation" and sort!="items_arrived" and sort!="-items_arrived":
        rjobs=rjobs.order_by(sort)
    elif sort and sort=="quotation":
        rjobs = rjobs.order_by("-quoted","quote_accepted")
    elif sort and sort=="-quotation":
        

        rjobs = rjobs.annotate(
            waiting=Case(
                When(quoted=True, quote_accepted=False, quote_declined=False, ),
                default=Value(False),
                output_field=BooleanField(),
            )
        ).order_by("-quote_accepted","waiting")
    elif sort=="items":
        rjobs = Job.objects.annotate(  total_required_qty=Sum("items__job_quantity")).order_by("total_required_qty")
    elif sort == "-items":
        rjobs = Job.objects.annotate(  total_required_qty=Sum("items__job_quantity")).order_by("-total_required_qty")


    paginator=Paginator(rjobs,25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    
    params = request.GET.copy()

    # Build querystring (without page)
    no_page = params.copy()
    no_page.pop("page", None)
    querystring = '&' + urlencode({k: v.strip() for k, v in no_page.items() if v and v.strip()})

    # Clean query (without sort)
    no_sort = params.copy()
    no_sort.pop("sort", None)
    clean_query = no_sort.dict()
    context={
            'jobs_count':rjobs.count(),
            'rjobs': page_obj,
            'page_obj':page_obj,
            'status':status,
            'querystring':querystring,
            'clean_query':clean_query,
            'sort':sort,
            'q':q,
            'quotation_status':quotation_status,
            'now_time':now_time,
            'age':age,

            }
    if request.method=='GET' and 'send_emails' in request.GET:
        date=request.GET.get("send_emails_date")
        if  date:
            try:
                jobs=Job.objects.filter(company=request.user.company,date=date,items__gt=0).distinct() 
            except:
                messages.error(request, "Please select a date before sending emails.")
                if view_option == "compact_view":
                    return redirect('inventory_compact')
                else:
                    return redirect('inventory')
            return render(request,'inventory/send_emails.html',{"date":date,'jobs':jobs })
        else:
            messages.error(request, "Please select a date before sending emails.")
    if 'confirm_sending' in request.POST:
        date=request.POST.get("date")
        job_ids = [int(i) for i in request.POST.getlist("job_ids")]
        jobs = Job.objects.filter(company=request.user.company,job_id__in=job_ids)
        send_multiple_emails(jobs,request)
        request.session['sent_jobs'] = job_ids
        request.session['sent_date'] = date
        return redirect('show_sent_emails')        
    # if date:
        #     jobs=Job.objects.filter(company=request.user.company,date=date)
            
        #     send_multiple_emails(jobs,request)
            
        # else:
        #     messages.error(request, "Please select a date before sending emails.")

    if request.method=='POST' and "reset_was_it_used" in request.POST:
        jobitem=JobItem.objects.get(id=pk)
        jobitem.was_it_used=False
        jobitem.is_used=False
        jobitem.save(update_fields=['is_used','was_it_used'],request=request)
        jobitem.job.save(update_fields=['status','items_arrived'],request=request,dont_save_history=True)
        if 'coming_from_job' in request.POST:
            return redirect('update_job', jobitem.job.job_id)
        else:
            if view_option == "compact_view":
                return render(request,'inventory/inventory_compact.html',{
                'rjobs': page_obj,
                'page_obj':page_obj,
                'status':'paused',
                'now_time':now_time
                })
            else:
                return render(request,'inventory/inventory.html',{
                    'rjobs': page_obj,
                    'page_obj':page_obj,
                    'status':'paused',
                    'now_time':now_time
                    })
    elif request.method=="POST" and 'job_is_ready' in request.POST:
        job=Job.objects.get(job_id=pk,company=request.user.company)
        if job.items.exclude(is_used=False).exists():
            messages.error(request,'There is a used item')
            # return render(request,'inventory/inventory.html',context)
        job.status='ready'
        job.save(request=request)#update_fields=['status']
        messages.success(request,"This job is now ready.")
        # return redirect('update_job', job.job_id)
        if view_option == "compact_view":
            return redirect('inventory_compact')
        else:
            return redirect('inventory')
    if 'coming_from_job' in request.POST:
        return redirect('update_job', jobitem.job.job_id)
    if request.method=="POST" and "job_id" in request.POST :

        job_id=request.POST.get("job_id")
        job=Job.objects.get(company=request.user.company,id=job_id)
        if 'change_quote_status' in request.POST :
            quote_status=request.POST.get("change_quote_status")

            if quote_status == "accepted":
                job.quote_accepted=True
                job.quote_declined=False
            elif quote_status == "declined":
                job.quote_accepted=False
                job.quote_declined=True

            else:
                job.quote_accepted=False
                job.quote_declined=False
            job.save(update_fields=["quote_accepted","quote_declined","status"],request=request)
        # if "change_from_date" in request.POST or "change_from_time" in request.POST or "change_to_time" in request.POST:
            


        if any(k in request.POST for k in ["change_from_date", "change_from_time", "change_to_time"]):            
            date_str = request.POST.get("change_from_date")
            from_time_str = request.POST.get("change_from_time")  # corrected name
            to_time_str = request.POST.get("change_to_time")
            date_value = parse_date(date_str) if date_str else job.date
            from_time_value = parse_time(from_time_str) if from_time_str else job.from_time
            to_time_value = parse_time(to_time_str) if to_time_str else job.to_time

            data = {
            "date": date_value.strftime("%Y-%m-%d") if date_value else "",
            "from_time": from_time_value.strftime("%H:%M:%S") if from_time_value else "",
            "to_time": to_time_value.strftime("%H:%M:%S") if to_time_value else "",
            "status": job.status,
            "company": job.company.id,
            "address": job.address,              # add required fields
            "job_id": job.job_id,
            "parent_account": job.parent_account
        }

            form = JobForm(data, instance=job)
            
            if form.is_valid():
                
                job = form.save(commit=False)
                job.save(update_fields=["date", "from_time", "to_time"],request=request)
                return redirect(request.path)
            # else:
            #     messages.error(request,f"{form.errors["to_time"][0] }")

            context["form"]=form
            context["form_job_id"]=job.job_id
        if "change_engineer" in request.POST:
            job_id=request.POST.get("job_id")
            job=Job.objects.get(company=request.user.company,id=job_id)
            engineer_id=request.POST.get("change_engineer",None)
            try:
                engineer=Engineer.objects.get(company=request.user.company,id=engineer_id)
            except:
                job.engineer=None
                job.save(request=request,update_fields=["engineer"])

                return render(request,'inventory/inventory_compact.html',context)

            if engineer:
                job.engineer=engineer
                job.save(request=request,update_fields=["engineer"])
        return render(request,'inventory/inventory_compact.html',context)

    if view_option == "compact_view":
        return render(request,'inventory/inventory_compact.html',context)
    else:
        return render(request,'inventory/inventory.html',context)
    
def show_sent_emails(request):
    # ✅ Retrieve from session
    job_ids = request.session.get('sent_jobs', [])
    date = request.session.get('sent_date')
    if not job_ids:
        return redirect('inventory')
    # Get updated jobs from DB
    jobs = Job.objects.filter(company=request.user.company, job_id__in=job_ids)

    # 🧹 Optional: clear after displaying once
    request.session.pop('sent_jobs', None)
    request.session.pop('sent_date', None)

    return render(request, 'inventory/show_sent_emails.html', {"date": date, "jobs": jobs,"jobs_count":jobs.count()})

def add_category(request):
    form=CategoriesForm()
    if request.method=='POST':
        form=CategoriesForm(request.POST)
        if form.is_valid():
            cat=form.save(commit=False)
            cat.company=request.user.company
            try:
                                
                exist_cat = Category.objects.get(Q(company=request.user.company), Q(category__icontains=cat.category))
                messages.error(request,f'A similar category exists: <span class="cat-highlight" style="color: rgb(230, 15, 15);">{exist_cat}</span>')
            except:
                cat.save(request=request)
                
                messages.success(request,f'Added <span class="cat-highlight" style="color: rgb(145, 34, 230);">{cat}</span> category successfully')
                   
           
    return render(request,'inventory/add_cat.html',{"form":form})

@login_required
def emails_history(request,):
    if request.method=="GET":
        if 'type' in request.GET :
            type=request.GET['type']
            if type!='all':
                emails=Email.objects.filter(company=request.user.company,type=type)
            else:
                emails=Email.objects.filter(company=request.user.company,)
        else:
            type='all'
            emails=Email.objects.filter(company=request.user.company,)
    return render(request,'inventory/emails.html',{'emails':emails.order_by('-date'),'type':type})
@login_required
def job_create(request):
    
    if request.method == 'POST':
        form = JobForm(request.POST)
        id=request.POST.get('job_id')  
        try:
            
            x=Job.objects.get(company=request.user.company,job_id=id)
            messages.error(request,"This job already exists")
            return redirect('update_job',id)
        except:
            pass
        if form.is_valid():
            try:
                Job.objects.get(job_id=form.cleaned_data['job_id'])
                jobi=True
            except Job.DoesNotExist:
                jobi=False
            if not jobi:
                job = form.save(commit=False)
                job.company = request.user.company
                job.save(request=request)
                
                messages.success(request, 'Job created successfully')
            else:
                messages.error(request,"This job already exists")
                id=form.cleaned_data['job_id']
                return redirect('update_job',id)
    else:
        form = JobForm(initial={'company':request.user.company})
    return render(request, 'inventory/job_create.html', {'form': form})
@login_required
def update_job(request, pk, cancel=0):
    
    job = Job.objects.get(job_id=pk, company=request.user.company)
    
    items=JobItem.objects.filter(job=job)
    items_count=job.items.all().count()
    form = JobForm(instance=job,updating=True,initial={'from_time':str(job.from_time),'to_time':str(job.to_time)})
    
    # comments_form=CommentForm(initial={
    #     'content_type': ContentType.objects.get_for_model(Job),
    #     'object_id': job.pk,
    #     'company': request.user.company,
    #     })
    
    comments = Comment.objects.filter(content_type=ContentType.objects.get_for_model(Job), object_id=job.pk,company=request.user.company)
    job_status=job.status

    if cancel==1 :
            
            li=[]
            li=[item for item in job.items.all() if (item.ordered or item.from_warehouse) and  item.arrived_quantity>0 and item.is_used==False ]
         
            if len(li)>0:
                request.session['job_post_data'] = request.POST
                return render(request,'inventory/confirm.html',{'items':li,'cancel_request':True,'job':job})
            job.status='cancelled'
            
            job.save(update_fields=['status'],request=request)
            # save_history(request,form)
            messages.success(request,'Now this job is cancelled')
            return redirect('update_job',pk=pk)
    if request.method=="POST":
        if 'hold' in request.POST:
            if 'on_hold' in request.POST:
                job.on_hold = False
            else:
                job.on_hold = True
            job.save(update_fields=['on_hold', 'status'], request=request)
            messages.success(request, 'Job updated')
            return redirect('update_job', pk=pk)
        if 'parts_attention' in request.POST:
          
            if 'parts_dont_need_attention' in request.POST:
                data=model_to_dict(job)
                data['parts_need_attention']=False
                form = JobForm(data, instance=job)
                if form.is_valid():
                    form.save()
                    messages.success(request,'Job updated')
                    return redirect('update_job',pk=pk)
                job.parts_need_attention = True
                # context={'form': form,'job':job,'comments':comments,'items':items,'items_count':items_count,'job_status':job_status}

    
                # return render(request, 'inventory/job_update.html', context)
                
            else:   
                data=model_to_dict(job)
                data['parts_need_attention']=True
                
                form = JobForm(data, instance=job)
                if form.is_valid():
                    
                    form.save()
                    messages.success(request,'Job updated')
                    return redirect('update_job',pk=pk)
                job.parts_need_attention = False
            # if 'parts_dont_need_attention' in request.POST:
            #     print(22222)
            #     job.parts_need_attention = False
            #     job.save(update_fields=['parts_need_attention','status'],request=request)
            #     print("DONNNT")
            # else:
            #     print(3333)

            #     job.parts_need_attention = True
            #     print("NEEEEED")
            #     job.save(update_fields=['parts_need_attention','status'],request=request)
            
      
            
        
        if  job.quoted :
            try:
                quote_status=request.POST.get('quote_status')
            except:
                quote_status=None
            
            if quote_status :
                if quote_status== 'quote_accepted' and not job.quote_accepted:
                    print("accepted")
                    job.quote_declined=False
                    job.quote_accepted=True
                    job.quoted=True
                    job.save(update_fields=['quote_declined','quote_accepted','quoted','status'],request=request)
                    messages.success(request,'Quote accepted')
                elif quote_status=='quote_declined' and not job.quote_declined:
                    print("PPP")
                    job.quote_declined=True
                    job.quote_accepted=False
                    job.quoted=True
                    job.save(update_fields=['quote_declined','quote_accepted','quoted','status'],request=request)
                    messages.success(request,'Quote declined')
                elif quote_status=='quote_unknown':
                    print(8980)
                    job.quote_declined=False
                    job.quote_accepted=False
                    job.quoted=True
                    job.save(update_fields=['quote_declined','quote_accepted','quoted','status'],request=request)

                return redirect('update_job',pk=pk)
        if 'yes_complete' in request.POST:
            post_data = request.session.pop('job_post_data', None)
            
            if post_data:
                form = JobForm(post_data, instance=job, updating=True)
                if form.is_valid():
                    obj=form.save(commit=False)
                    
                    obj.save(request=request)
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
            form = JobForm(request.POST, instance=job)
            
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
                
                if form.changed_data:
                    obj = form.save(commit=False)  
                    obj.save(request=request)
                    form = JobForm(request.POST, instance=job,updating=True)
                
                    messages.success(request, 'Job updated successfully')
                    items=JobItem.objects.filter(job=job)
                
                    return redirect('update_job',job.job_id)
                else:
                    messages.error(request, 'No change')
                    return redirect('update_job',job.job_id)
                
            
        comments_form=CommentForm(request.POST)
        if comments_form.is_valid() and 'add_comment' in request.POST: 
            comment = comments_form.save(commit=False)
            comment.added_by = request.user 
            comment.company = request.user.company
            comment.save()
            comments = Comment.objects.filter(content_type=ContentType.objects.get_for_model(Job), object_id=job.pk,company=request.user.company)
            comments_form = CommentForm(initial={
            'content_type': ContentType.objects.get_for_model(Job),
            'object_id': job.pk,
            'company': request.user.company,
            })
            form = JobForm(instance=job,updating=True)
        if 'send_email' in request.POST :
                comments = Comment.objects.filter(content_type=ContentType.objects.get_for_model(Job), object_id=job.job_id,company=request.user.company)
                comments_form = CommentForm(initial={
                'content_type': ContentType.objects.get_for_model(Job),
                'object_id': job.job_id,
                'company': request.user.company,
                })
                form = JobForm(instance=job,)
                items=JobItem.objects.filter(job=job)
                if job.engineer is None  :

                    messages.error(request,"You must assign an engineer for this job")
                    return render(request, 'inventory/job_update.html', {'form': form,'job':job,'comments_form':comments_form,'comments':comments,'items':items,'items_count':items_count,'job_status':job_status})       
                elif  job.status!="ready"   :
                    messages.error(request,"Job must be ready")
                    return render(request, 'inventory/job_update.html', {'form': form,'job':job,'comments_form':comments_form,'comments':comments,'items':items,'items_count':items_count,'job_status':job_status})       

                if job.engineer is not None and job.status=="ready":

            
                    send_multiple_emails([job],request,single=True,)
                    # Email.objects.create(type=Email.EmailType.SINGLE,company=request.user.company,user=request.user,to=recipient_list,subject=subject,body=message,date=timezone.now())
                    messages.success(request,f'Email sent to {job.engineer.name}')
                    form = JobForm(instance=job,updating=True,)
                    comments_form=CommentForm(initial={
                        'content_type': ContentType.objects.get_for_model(Job),
                        'object_id': job.job_id,
                        'company': request.user.company,
                        })
                    comments = Comment.objects.filter(content_type=ContentType.objects.get_for_model(Job), object_id=job.job_id,company=request.user.company)
                    return render(request, 'inventory/job_update.html', {'form': form,'job':job,'comments_form':comments_form,'comments':comments,'items':items,'items_count':items_count,'job_status':job_status})       
    comments_form=CommentForm(initial={
        'content_type': ContentType.objects.get_for_model(Job),
        'object_id': job.pk,
        'company': request.user.company,
        })
    
    context={'form': form,'job':job,'comments_form':comments_form,'comments':comments,'items':items,'items_count':items_count,'job_status':job_status}

    
    return render(request, 'inventory/job_update.html', context)       
###########################-ITEM-######################
@login_required
def item_add(request,pk=None,):
    try:
        job=Job.objects.filter(company=request.user.company).get(job_id=pk)
    except Job.DoesNotExist:
        job=None
    
    form=JobItemForm()
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
                    warehouse_items=WarehouseItem.objects.filter(company=request.user.company,warehouse_quantity__gt=0,part_number__iexact=query)
                return render(request, 'inventory/add_item.html', {'form': form,'job':job,'warehouse_items':warehouse_items,'query':query,'show_stock':True})

        if 'adding_from_stock' in request.POST:
            
            form=JobItemForm(request.POST,)
            item_id = request.POST.get('selected_item_id')
            required_quantity = int(request.POST.get('required_quantity'))
            print(item_id)
            
            item=WarehouseItem.objects.get(Q(company=request.user.company)&Q(id=item_id))
            
            try:
                with transaction.atomic():
                    if required_quantity<=0:
                        messages.error(request,"Quantity must be positive integer")
                        form=JobItemForm()
                        warehouse_items=warehouse_items
                        return render(request, 'inventory/add_item.html', {'form': form,'job':job,'warehouse_items':warehouse_items})
        
                    if item.warehouse_quantity>0 and item.warehouse_quantity>= required_quantity:
                            x=JobItem(
                            job=job,
                            name=item.name,
                            part_number=item.part_number,
                            price=item.price,
                            reference=item.reference,
                            supplier=item.supplier,
                            added_date=item.added_date,
                            added_by=item.added_by,
                            from_warehouse=True, #if item.is_moved_from_job==None else False,
                            added_by_batch_entry=item.added_by_batch_entry,
                            company=request.user.company,
                            arrived=True,
                            job_quantity=+required_quantity,
                            arrived_quantity=+required_quantity,
                            category=item.category,
                            was_for_job=item.is_moved_from_job if item.is_moved_from_job else None
                            )
                            x.save(request=request)
                            item.warehouse_quantity=item.warehouse_quantity-required_quantity
                            # item_save(item)
                            item.save(update_fields=['warehouse_quantity'],request=request)#
                            if item.warehouse_quantity==0:
                                item.delete()
                              
                    else:
                        messages.error(request,"Not enough stock")
                        form=JobItemForm()
                        warehouse_items=warehouse_items
                        return render(request, 'inventory/add_item.html', {'form': form,'job':job,'warehouse_items':warehouse_items,'show_stock':True})
            except IntegrityError:
                messages.error(request,"Failed")
                form=JobItemForm()
                warehouse_items=warehouse_items
                return render(request, 'inventory/add_item.html', {'form': form,'job':job,'warehouse_items':warehouse_items,'show_stock':True})

            messages.success(request, 'Item added from stock successfully')
            form=JobItemForm()
            warehouse_items=warehouse_items
            return render(request, 'inventory/add_item.html', {'form': form,'job':job,'warehouse_items':warehouse_items,'show_stock':True})
        elif 'adding_new' in request.POST:
            form=JobItemForm(request.POST)
            
            if form.is_valid():
                
                try:
                    with transaction.atomic():
                        
                        
                        # category=form.cleaned_data['category']
                        if pk is not None:
                            jobitem=form.save(commit=False)
                            jobitem.company=request.user.company
                            jobitem.job=job
                            jobitem.was_for_job=job
                            jobitem.save(request=request)
                       
                            form=JobItemForm()
                            warehouse_items=warehouse_items
                            messages.success(request, f'{jobitem}-is added to job {job}')
                            
                            return render(request, 'inventory/add_item.html' , {'form': form,'warehouse_items':warehouse_items,'job':job})
                except IntegrityError:
                    
                    messages.error(request, f'{jobitem.name}{Exception} — failed')
                    return render(request, 'inventory/add_item.html', {'form': form,'job':job,'warehouse_items':warehouse_items})
    warehouse_items=warehouse_items
    return render(request, 'inventory/add_item.html', {'form': form,'job':job,'warehouse_items':warehouse_items})
def add_warehouseitem(request):
    
    form=WarehouseitemForm()
    if request.method=='POST':
            form=WarehouseitemForm(request.POST)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        warehouse_item=form.save(commit=False)
                        warehouse_item.company=request.user.company
                        warehouse_item.aadded_by=request.user
                        warehouse_item.save(request=request)
                        messages.success(request, f'{warehouse_item}-is added to warehouse')
                        form=WarehouseitemForm()
                        return render(request, 'inventory/add_item.html',{'form': form,})

                except IntegrityError:
                    messages.error(request, f'{warehouse_item} — failed') 
    return render(request, 'inventory/add_item.html',{'form': form,})

@login_required
def update_item(request, pk):
    # import random
    # import string
    item = JobItem.objects.get(Q(id=pk) & Q(job__company=request.user.company))
    # item.reference=random.choices(string.ascii_uppercase  + string.digits, k=6)
    # item.save(request=request)
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
                # job_item.job.status='cancelled'
                job_item.was_it_used=False
                job_item.save(request=request)
                
                # job_item.job._current_user = request.user
                # job_item.job.save(user=request.user)#update_fields=['status']
                if next_url:
                    return redirect(next_url)
        elif 'yes_move' in request.POST:
            next_url = request.POST.get('next')
            
            try:
                job_item = item
                # Optional: Check if already used or empty
                if job_item.is_used or job_item.arrived_quantity == 0:
                    
                    messages.error(request, "Nothing to move or already used.")
                    return render(request, 'inventory/update_item.html', {'form':form})
                # try:
                #     WarehouseItem.objects.get(Q(company=request.user.company) & Q(item=item.item))
                #     create_new=False
                # except:
                #     create_new=True
                # if not job_item.from_warehouse or create_new :
                job=job_item.was_for_job if job_item.was_for_job else job
                # Create WarehouseItem
                x=WarehouseItem(
                    
                    name=job_item.name,
                    part_number=job_item.part_number,
                    price=job_item.price,
                    supplier=job_item.supplier,
                    added_date=job_item.added_date,
                    added_by=job_item.added_by,
                    warehouse_quantity=job_item.arrived_quantity,
                    company=request.user.company,
                    
                    reference=job_item.reference,
                    category=job_item.category,
                    #is_used=job_item.is_used,
                    is_moved_from_job=job if job_item.was_for_job else None  ,   
                    
                )
                x.save(request=request)
                    
                # else:
                
                #     try:
                #         wi=WarehouseItem.objects.get(Q(item=job_item.item) & Q(is_moved_from_job=True))
                #     except:
                        
                #         wi=WarehouseItem.objects.get(item=job_item.item)
                #     wi.warehouse_quantity+=job_item.job_quantity
                #     wi.save(update_fields=['warehouse_quantity'],request=request)
                # # Delete JobItem after successful move
                # job_item.job.status='cancelled'
                
                # job_item.job.save()
                job_item.delete()
                # messages.success(request,"Item moved to warehouse")
            except JobItem.DoesNotExist:
                messages.error(request,"Moving failed")
            if next_url:
                print(next_url)
                return redirect(next_url)
            
                return redirect('update_job' ,pk=job)
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
                    item.delete(request=request)
                    messages.success(request,f'{item} deleted succssefully')
            except:
                messages.error(request,f'{item} deleting failed')
                return redirect(f'update_item',pk=pk)
            return redirect('inventory')
        elif 'no_return_back' in request.POST:
            return redirect(f'update_item',pk=pk)
        form = JobItemForm(request.POST, request.FILES, instance=item,)
        if 'move_item' in request.POST :
            try:
                job_item = item
                job=job_item.job
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
                # try:
                #     WarehouseItem.objects.get(Q(company=request.user.company) & Q(item=item.item))
                #     create_new=False
                # except:
                #     create_new=True
                # if not job_item.from_warehouse or create_new :
                job=job_item.was_for_job if job_item.was_for_job else job_item.job
                # Create WarehouseItem
                x=WarehouseItem(
                    name=job_item.name,
                    part_number=job_item.part_number,
                    price=job_item.price,
                    supplier=job_item.supplier,
                    company=request.user.company,   
                    added_by_batch_entry=job_item.added_by_batch_entry,
                    added_by=request.user,
                    warehouse_quantity=job_item.arrived_quantity,
                    reference=job_item.reference,
                    
                    category=job_item.category,
                    #is_used=job_item.is_used,
                    is_moved_from_job=job if job_item.was_for_job else None  ,   
                )
                x.save(request=request)
                    
                # else:
                
                #     try:
                #         wi=WarehouseItem.objects.get(Q(item=job_item.item) & Q(is_moved_from_job=True))
                #     except:
                        
                #         wi=WarehouseItem.objects.get(item=job_item.item)
                #     wi.warehouse_quantity+=job_item.job_quantity
                #     wi.save(update_fields=['warehouse_quantity'],request=request)
                # Delete JobItem after successful move
                job_item.delete() 
                messages.success(request,"Item moved to warehouse")
            except JobItem.DoesNotExist:
                messages.error(request,"Moving failed")
            return redirect('inventory') 
        form = JobItemForm(request.POST, request.FILES, instance=item,)
        comments_form=CommentForm(request.POST)
        prevq=item.job_quantity
        
        if form.is_valid() and 'edit' in request.POST  :
            print("SSS")
            job_quantity=form.cleaned_data['job_quantity']
            print(job_quantity)
            if item.from_warehouse:
                job_quantity=form.cleaned_data['job_quantity']

               
            # -------- CASE 1: increase quantity --------
                if job_quantity > prevq:
                    needed = job_quantity - prevq

                    # Try with reference first, fallback without
                    witem = (
                        WarehouseItem.objects
                        .filter(company=request.user.company,
                                part_number=item.part_number,
                                warehouse_quantity__gt=0,
                                reference=item.reference)
                        .first()
                    ) or (
                        WarehouseItem.objects
                        .filter(company=request.user.company,
                                part_number=item.part_number,
                                warehouse_quantity__gt=0)
                        .first()
                    )

                    if witem:
                        if witem.warehouse_quantity >= needed:
                            item.job_quantity = job_quantity
                            witem.warehouse_quantity -= needed
                            witem.save(update_fields=['warehouse_quantity'], request=request)
                            item.save(update_fields=['job_quantity'], request=request)
                        else:
                            messages.error(
                                request,
                                f"Not enough stock, only {witem.warehouse_quantity} available"
                            )
                            return render(request, 'inventory/update_item.html',
                                        {'form': form,'item': item,
                                        'comments_form': comments_form,
                                        "comments": comments})
                    else:
                        messages.error(request, "This part is not in the stock, please order.")
                        return render(request, 'inventory/update_item.html',
                                    {'form': form,'item': item,
                                    'comments_form': comments_form,
                                    "comments": comments})

                # -------- CASE 2: decrease quantity --------
                elif prevq > job_quantity:
                    diff = prevq - job_quantity

                    witem = (
                        WarehouseItem.objects
                        .filter(company=request.user.company,
                                part_number=item.part_number,
                                reference=item.reference)
                        .first()
                    ) or (
                        WarehouseItem.objects
                        .filter(company=request.user.company,
                                part_number=item.part_number)
                        .first()
                    )

                    if witem:
                        witem.warehouse_quantity += diff
                        witem.save(update_fields=['warehouse_quantity'], request=request)
                    else:
                        witem = WarehouseItem.objects.create(
                            company=request.user.company,
                            name=item.name,
                            part_number=item.part_number,
                            price=item.price,
                            supplier=item.supplier,
                            added_date=item.added_date,
                            added_by=item.added_by,
                            category=item.category,
                            warehouse_quantity=diff,
                            reference=item.reference,
                            is_used=False,
                            is_moved_from_job=item.job,
                        )
                        witem.save(request=request)

                    item.job_quantity = job_quantity
                    item.save(update_fields=['job_quantity',], request=request)

                    if item.job_quantity < 1:
                        jobid = item.job.job_id
                        item.delete(request=request)
                        messages.success(request, f"Moved {diff} of {item} to warehouse successfully")
                        return redirect('update_job', jobid)

                    messages.success(request, f"Moved {diff} of {item} to warehouse successfully")
                    return render(request, 'inventory/update_item.html',
                                {'form': JobItemForm(instance=item),
                                'item': item,
                                'comments_form': comments_form,
                                "comments": comments})

                # -------- CASE 3: same quantity --------
                else:
                    item = form.save(commit=False)
                    item.save(request=request)
                    messages.success(request, "Part updated successfully")
                    return render(request, 'inventory/update_item.html',
                                {'form': JobItemForm(instance=item),
                                'item': item,
                                'comments_form': comments_form,
                                "comments": comments})

        # -------- CASE: not from warehouse --------
            else:
                print("OOOOOOOOOOOOOOOOOOOOOOOOOO")
                item = form.save(commit=False)
                item.save(request=request)
                print(item.ordered_date)
                return redirect("update_item",item.id)
                return render(request, 'inventory/update_item.html',
                            {'form': form,
                            'item': item,
                            'comments_form': comments_form,
                            "comments": comments})

        # fallback context
        
        return render(request, 'inventory/update_item.html',
                {'form': form,'item': item,
                'comments_form': comments_form,
                "comments": comments,
                "completed": completed})
                
   
    # form = JobItemForm(instance=item,)#,updating=True,completed=completed
    comments_form=CommentForm(initial={
        'content_type': ContentType.objects.get_for_model(JobItem),
        'object_id': item.id,
        'company': request.user.company,
        })
    comments= Comment.objects.filter(content_type=ContentType.objects.get_for_model(JobItem), object_id=item.id,company=request.user.company)
    context = {'form': form,'item': item,'comments_form':comments_form,"comments":comments,"completed":completed}
    return render(request, 'inventory/update_item.html', context)
########################
@owner_only
def history(request):
    company=request.user.company    
    selected_user_id = request.GET.get('user_id', 'all')
    date = request.GET.get('date', 'all')
    users=CustomUser.objects.filter(company=company)
    try:
        model=request.GET['model']
    except:
        pass
    if request.method=='GET' and 'model' in request.GET and model!='all':
        model=model
        
        history=History.objects.filter(company=company, content_type__model=model).order_by('-changed_at')
    else:
        model='all'
        history=History.objects.filter(company=company).order_by('-changed_at')
    if selected_user_id!='all':
        user=CustomUser.objects.get(Q(company=company) & Q(id=selected_user_id))
        history=history.filter(user=user)
    if date!='all':
        try:
            date=datetime.strptime(date, "%Y-%m-%d").date()
            history=history.filter(changed_at__date=date)
        except:
            pass
    models_filter=['job','warehouseitem','jobitem','customuser','company']

    
    paginator=Paginator(history.order_by('-changed_at'),25)
    page_number = request.GET.get('page')
    print(page_number)
    page_obj = paginator.get_page(page_number)
    
    return render(request,'inventory/history.html',{'history':page_obj,'page_obj':page_obj,'model':model,'users':users,'selected_user_id':selected_user_id,'models_filter':models_filter})


@login_required
def update_warehouse_item(request, pk):
    warehouse_item = WarehouseItem.objects.get(Q(company=request.user.company),Q(id=pk))
    
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
        
        comments_form=CommentForm(request.POST)
        if comments_form.is_valid() and "just_add_comment" in request.POST :
        
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
            context = {'form': form,'warehouse_item': warehouse_item,'comments_form':comments_form,"comments":comments}
            return render(request, 'inventory/update_warehouse_item.html', context)
        if "delete" in request.POST:
            return render(request,'inventory/confirm.html',{'warehouse_item':warehouse_item,'warehouse_item':True})
        
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
            
            warehouse_quantity=form.cleaned_data['warehouse_quantity']
            warehouse_item=form.save(commit=False)
            warehouse_item.warehouse_quantity=warehouse_quantity
            warehouse_item.save(request=request)
            
            form = WarehouseitemForm( instance=warehouse_item,)
            messages.success(request,f'Item {warehouse_item} updated successfully')
            context = {'form': form,'warehouse_item': warehouse_item,'comments_form':comments_form,"comments":comments}
            return render(request, 'inventory/update_warehouse_item.html', context)
    context = {'form': form,'warehouse_item':warehouse_item,'comments_form':comments_form,"comments":comments}
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


@owner_only
def admin_panel(request): 
        if request.user.company.owner==request.user:
            
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
        form=registerworker(instance=worker,request=request,enable_edit=True,updating=True,changing_password=True)
        return render(request, 'inventory/update_user.html',{'form':form,'editing':True,'changing_password':True})
    if request.method=='POST' and 'confirm_new_password' in request.POST:
        print("PP")
        form=registerworker(request.POST,instance=worker,enable_edit=True,updating=True,changing_password=True)
        if form.is_valid():
            x=form.save(commit=False)
            x.save(request=request)
            form=registerworker(instance=worker,enable_edit=False,updating=True,)
            messages.success(request,'Password changed successfully')
        return render(request, 'inventory/update_user.html',{'form':form,'editing':False,'changing_password':False})
    if request.method=='POST' and 'edit' in request.POST:

        form=registerworker(instance=worker,request=request,enable_edit=True,updating=True,)
        return render(request, 'inventory/update_user.html',{'form':form,'editing':True})

    if request.method=='POST' and 'update' in request.POST:
        worker_email=worker.email
        form=registerworker(request.POST,request=request,instance=worker,enable_edit=True,updating=True,)
        if form.is_valid():

            form.save(commit=False)
            email=form.cleaned_data['email']
            print(email,worker_email)
            if email!=worker_email:
                request.session['verifying']="updating_user"
                request.session['username'] = form.cleaned_data['username']
                request.session['register_email'] = email
                request.session['worker_id']=worker.id
                otp=generate_otp()
                
                request.session['otp_generated_at']=time.time()
                request.session['user_updating_otp']=otp
                send_otp_email(email,otp)
                return redirect('otp')
            else:
                form.save(request=request)
                messages.success(request,'User updated successfully')
            
            
            form=registerworker(instance=worker,enable_edit=False,updating=True,)
            return render(request, 'inventory/update_user.html',{'form':form})
        return render(request, 'inventory/update_user.html',{'form':form,'editing':True,'worker':worker})

    return render(request, 'inventory/update_user.html',{'form':form,'editing':False,'worker':worker})


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
    worker_id=request.session.get('worker_id')
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
        if (
            input_user_otp == user_session_otp and
            otp_generated_at is not None and
            (time.time() - otp_generated_at <= otp_expiry_seconds)
        ):
            username = request.session.get('username')
            user=CustomUser.objects.get(id=worker_id)
            user.email=email
            user.username=username
            
            user.save(update_fields=['username','email',],request=request)
            for k in ['username','register_email','otp_generated_at','worker_id']:
                request.session.pop(k,None)
            messages.success(request,"User updated successfully")
            return redirect('update_user',worker_id)
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
            company.save(update_fields=['company_name','company_email','address','phone'],request=request)
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
                    input_email_otp == email_session_otp and
                    input_company_otp==company_session_otp and
                    otp_generated_at is not None and
                    (time.time() - otp_generated_at <= otp_expiry_seconds)
                ):
            
            with transaction.atomic():
                # try:
                    company_data = request.session.get('company_data')
                    user_data = request.session.get('user_data').copy()  # Make a copy so we can modify safely
                    user_data.pop('password2', None)  # Remove password2 if it exists
                    
                    user_data['password'] = make_password(user_data['password'])
                    company = Company(**company_data,)
                    company.save(dont_save_history=True)
                    user = CustomUser(company=company, **user_data,)
                    user.save(dont_save_history=True)
                    user.is_owner=True
                    company.owner=user
                    company.save(update_fields=['owner'],dont_save_history=True)
                    user.save(update_fields=['is_owner'],dont_save_history=True)
                    History.objects.create(
                    content_type=ContentType.objects.get_for_model(company),
                    object_id=company.pk,  # now PK is available
                    company=company,
                    field="",
                    old_value="",
                    new_value="",
                    user=user ,
                    created=True
                    )
                    # Optionally log the user in
                    request.session.flush()

                    messages.success(request,'Company created successfully')
                    return redirect('login')
                # except:
                #     messages.error(request,'Failed creating company. Try again')
        else:
            messages.error(request,"Wrong OTP. Try again")
    left_time = otp_expiry_seconds - (time.time() - otp_generated_at) 
    left_time=left_time if left_time>0 else "Expired"
    return render(request, 'auths/otp.html', {'email':email,'company_email':company_email,'left_time':left_time})
@owner_only
def company_settings(request):
    company = request.user.company  # assuming each user belongs to a company
    settings, created = CompanySettings.objects.get_or_create(company=company)

    if request.method == 'POST':
        form = CompanySettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, "Company settings updated successfully.")
            return redirect('company_settings')  # name of this view in urls.py
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CompanySettingsForm(instance=settings)

    return render(request, 'inventory/company_settings.html', {'form': form})



def warehouse(request, ):
    
    items_status=request.GET.get('items_status') if request.GET.get('items_status') else 'available'
    q=request.GET.get("q") if request.GET.get("q") else ''
    warehouse_items=WarehouseItem.objects.filter(company=request.user.company)
    used_warehouse_items=JobItem.objects.filter(company=request.user.company,is_used=True,from_warehouse=True)
    taken_warehouse_items=JobItem.objects.filter(company=request.user.company,is_used=False,from_warehouse=True)
    if request.GET.get("entry_method")=='batch_entry' :
        warehouse_items=warehouse_items.filter(added_by_batch_entry=True)#,is_moved_from_job=None
        used_warehouse_items=JobItem.objects.filter(added_by_batch_entry=True)
        taken_warehouse_items=JobItem.objects.filter(added_by_batch_entry=True)    
    elif request.GET.get("entry_method")=='normal_entry':
        warehouse_items=WarehouseItem.objects.filter(added_by_batch_entry=False)#,is_moved_from_job=None
        used_warehouse_items=JobItem.objects.filter(added_by_batch_entry=False)
        taken_warehouse_items=JobItem.objects.filter(added_by_batch_entry=False)    
    if q:
        warehouse_items=warehouse_items.filter(Q(name__icontains=q) | Q(part_number__icontains=q) | Q(reference__icontains=q) | Q(supplier__icontains=q) | Q(category__category__icontains=q))
        used_warehouse_items=used_warehouse_items.filter(Q(name__icontains=q) | Q(part_number__icontains=q) | Q(reference__icontains=q) | Q(supplier__icontains=q) | Q(category__category__icontains=q))
        taken_warehouse_items=taken_warehouse_items.filter(Q(name__icontains=q) | Q(part_number__icontains=q) | Q(reference__icontains=q) | Q(supplier__icontains=q) | Q(category__category__icontains=q))
    entry_method=request.GET.get("entry_method")
    return render(request,'inventory/warehouse.html',{'warehouse_items':warehouse_items,'used_warehouse_items':used_warehouse_items,'taken_warehouse_items':taken_warehouse_items,'entry_method':entry_method,'items_status':items_status})


def review_ordered_items(request,):
    
    sort=request.GET.get("sort",None)
    q=request.GET.get("q",None)
    items_status=request.GET.get("items_status",None)
    ordered_from_date=request.GET.get("ordered_from_date",None)
    ordered_to_date=request.GET.get("ordered_to_date",None)
    if items_status=="arrived":
        items=JobItem.objects.filter(company=request.user.company,is_used=False,from_warehouse=False,ordered=True,arrived=True)
    elif items_status=="not_arrived":
        items=JobItem.objects.filter(company=request.user.company,is_used=False,from_warehouse=False,ordered=True,arrived=False)
    elif ordered_from_date or ordered_to_date:

    # Convert the strings to date objects only once
        from_date = datetime.strptime(ordered_from_date, '%Y-%m-%d').date() if ordered_from_date else None
        to_date = datetime.strptime(ordered_to_date, '%Y-%m-%d').date() if ordered_to_date else None

        # If both dates entered → validate range
        if from_date and to_date:
            if from_date > to_date:
                messages.error(request, "The 'From' date cannot be later than the 'To' date.")
                return redirect('review_ordered_items')

            items = JobItem.objects.filter(
                company=request.user.company,
                is_used=False,
                from_warehouse=False,
                ordered=True,
                ordered_date__gte=from_date,
                ordered_date__lte=to_date
            )

        # If only from_date
        elif from_date:
            items = JobItem.objects.filter(
                company=request.user.company,
                is_used=False,
                from_warehouse=False,
                ordered=True,
                ordered_date__gte=from_date
            )

        # If only to_date
        elif to_date:
            items = JobItem.objects.filter(
                company=request.user.company,
                is_used=False,
                from_warehouse=False,
                ordered=True,
                ordered_date__lte=to_date
            )

            

    else:
        items=JobItem.objects.filter(company=request.user.company,is_used=False,from_warehouse=False,ordered=True)
    if sort:

        items=items.order_by(sort)
    if q:
        items=items.filter(Q(name__icontains=q)|Q(part_number__icontains=q))
    

    paginator=Paginator(items,30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    params = request.GET.copy()

    # Build querystring (without page)
    no_page = params.copy()
    no_page.pop("page", None)
    querystring = '&' + urlencode({k: v.strip() for k, v in no_page.items() if v and v.strip()})

    # Clean query (without sort)
    no_sort = params.copy()
    no_sort.pop("sort", None)
    clean_query = no_sort.dict()
    if request.method=="POST" :
        arrived=int(request.POST.get("arrived"))
        item_id=request.POST.get("item_id")
        item=JobItem.objects.get(company=request.user.company,id=item_id)
        item.arrived_quantity=arrived
        item.save(request=request,update_fields=["arrived_quantity","arrived"])
        messages.info(request,f"{arrived} parts of {item} arrived for {item.job.address}")
        return redirect('review_ordered_items')
    
    return render(request,'inventory/review_ordered_items.html',{'items':page_obj,"sort": sort,"clean_query": clean_query,'items_status':items_status,'querystring':querystring,'page_obj':page_obj})




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
              
                eng.save(request=request)
                messages.success(request,f"Engineer {eng.name} is added")
            else:
                messages.error(request,"Engineer with the same name exists")
            return render(request,'inventory/eng.html',{'form':form})
    return render(request,'inventory/eng.html',{'form':form})
def update_engineer(request,pk):
    eng=Engineer.objects.get(Q(company=request.user.company) & Q(pk=pk))
    form=EngineerForm(instance=eng,updating=True)
    if request.method=='POST' and 'enable_editing' in request.POST:
        form=EngineerForm(instance=eng,updating=True,enable_editing=True)
        enable_editing=True
    else:
        enable_editing=False
    if request.method=="POST" and "edit" in request.POST:
       form=EngineerForm(request.POST,instance=eng,updating=True)
       if form.is_valid:
            eng=form.save(commit=False)
            try:
                Engineer.objects.get(Q(name=eng.name) & Q(company=request.user.company) & ~Q(pk=pk))
                ex=True
            except Engineer.DoesNotExist:
                ex=False
            if not ex:
                eng.company=request.user.company
              
                eng.save(request=request)
                messages.success(request,f"Engineer {eng.name} is updated")
            else:
                messages.error(request,"Engineer with the same name exists")
            return render(request,'inventory/update_eng.html',{'form':form,'eng':eng,'enable_editing':enable_editing})
    return render(request,'inventory/update_eng.html',{'form':form,'eng':eng,'enable_editing':enable_editing})
def search_view(request):
    form=SearchForm()
    return render(request,'inventory/inventory.html',{'form':form})
def create_batch_items(request):
    
    if request.method == 'POST':
        cat_val = request.POST.get('category')
        if cat_val:
            try:
                cat_obj=Category.objects.get(category__icontains=cat_val)
            except Category.DoesNotExist:
                try:
                    cat_obj=Category.objects.get(category='Others')
                except Category.DoesNotExist:
                    cat_obj=Category(company=request.user.company,category='Others')
                    cat_obj.save(request=request)
        else:
            try:
                cat_obj=Category.objects.get(category='Others')
            except Category.DoesNotExist:
                cat_obj=Category(company=request.user.company,category='Others')
                cat_obj.save(request=request)
        item_data = {
            'name': request.POST['name'],
            'part_number': request.POST['part_number'],
            'reference': request.POST['reference'],
            'price': float(request.POST['price']) ,
            'supplier': request.POST['supplier'],
            'warehouse_quantity': int(request.POST['warehouse_quantity']),
            'company':request.user.company,
            'category': cat_obj,
        }
        wi=WarehouseItem(name=item_data['name'],
                         part_number=item_data['part_number'],
                         reference=item_data['reference'],
                         price=item_data['price'],
                         supplier=item_data['supplier'],
                         warehouse_quantity=item_data['warehouse_quantity'],
                         company=item_data['company'],
                         category=item_data['category'],
                         added_by_batch_entry=True,
                         )
        wi.save(request=request)
        
        messages.success(request,f'{item_data['warehouse_quantity']} of {wi.name} added to the warehouse')
        # Remove this item from session
        items = request.session.get('batch_items', [])
        items = [item for item in items if item['part_number'] != item_data['part_number']]
        request.session['batch_items'] = items
        return redirect('batch_entry')

import pandas as pd
def batch_entry(request):
    c=Category.objects.filter(company=request.user.company)
    print(c)
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



def impot_jobs(request):
    if request.method == 'POST' and request.FILES.get('jobs_sheet'):
        excel_file = request.FILES['jobs_sheet']

        COLUMNS = {
            'Job#': 'job_id',
            'Date': 'date',
            'Time': 'from_time',
            'Status': 'status',
            'Parent Customer': 'parent_account',
            'Service Location Address 1': 'address',
            'Service Location Zip': 'postcode',
            'Tech(s) Assigned': 'engineer',
            'Completion Notes':'notes',
            'Job Created At': 'birthday',

        }

        df = pd.read_excel(excel_file, usecols=COLUMNS.keys())
        df.rename(columns=COLUMNS, inplace=True)

        # --- NORMALIZATION (CRITICAL PART) ---

        # Dates / timestamps → string
        for col in ['date', 'birthday']:
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda x: (
                        None
                        if pd.isna(x)
                        else x.strftime('%Y-%m-%d %H:%M:%S')
                        if isinstance(x, (pd.Timestamp, datetime))
                        else str(x)
                    )
                )
        # Time columns → string
        if 'from_time' in df.columns:
            df['from_time'] = df['from_time'].apply(
            lambda x: x.strftime('%H:%M:%S') if pd.notnull(x) else None
                )


        # NaN / NaT → None (JSON safe)
        df = df.where(pd.notnull(df), None)
        data=df.to_dict(orient='records')
        # # ------------------------------------

        request.session['batch_jobs'] = data
        request.session.set_expiry(30* 60) 
        return redirect('jobs_batch_entry')

    # Load current items from session
    data = request.session.get('batch_jobs', [])
    return render(request, 'inventory/jobs_batch_entry.html', {'data': data})

def create_batch_jobs(request):
    
        
                
        
        INVALID_VALUES = {None, '', 'None', 'nan', 'NaN'}

        def parse_time(value):
            if value in INVALID_VALUES:
                return None

            # Already a time object (pandas sometimes does this)
            # if isinstance(value, time):
            #     return value

            value = str(value).strip()

            for fmt in ('%H:%M', '%H:%M:%S', '%Y-%m-%d %H:%M:%S'):
                try:
                    return datetime.strptime(value, fmt).time()
                except ValueError:
                    continue

            return None  # silently ignore invalid formats
        def parse_this_date(value):
            if value in INVALID_VALUES:
                return None

            value = str(value).strip()

            # Try multiple date formats (add more if needed)
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S'):
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue

            return None
        job_data = {
            'job_id': request.POST.get('job_id'),

            'date': parse_this_date(request.POST.get('date')),
            'from_time': parse_time(request.POST.get('from_time')),

            'status': request.POST.get('status'),
            'parent_account': request.POST.get('parent_account'),
            'address': request.POST.get('address'),
            'postcode': request.POST.get('postcode'),

            'engineer': request.POST.get('engineer'),
            'notes': request.POST.get('notes'),

            'birthday': request.POST.get('birthday'),

            'company': request.user.company,
        }
        engineer=Engineer.objects.filter(company=request.user.company,name__icontains=job_data['engineer']).first()
        job_status={
            'Paused':'paused',
            'Unscheduled':'ready',
            'Scheduled':'ready',
            'Cancelled':'cancelled',
            'Completed':'completed'

        }
       
        try:
            
            x=Job.objects.get(company=request.user.company,job_id=job_data['job_id'])
            items = request.session.get('batch_jobs', [])
        

            items = [item for item in items if int(item['job_id']) != int(job_data['job_id'])]
            request.session['batch_jobs'] = items
            messages.error(request,f"Job {x.job_id} already exists")
            return redirect('jobs_batch_entry')
        except:
            pass
        job=Job(
                        company=request.user.company,
                        job_id=job_data['job_id'],
                        date=job_data['date'],
                        from_time=job_data['from_time'],
                        post_code=job_data['postcode'],
                        parent_account=job_data['parent_account'],
                        address=job_data['address'],
                        engineer=engineer,
                        birthday=job_data['birthday'],
                        imported_from_sheet=True,
                            )
        job.status = job_status.get(job_data['status'], 'ready')
        if job.status=='paused':
            job.parts_need_attention=True
        job.save(request=request)
        if job_data['notes']  != "None":
            comment=Comment(
                company=request.user.company,
                content_type=ContentType.objects.get_for_model(Job), object_id=job.id, 
                comment=job_data['notes'],
                added_by=request.user,
            )
            comment.save()
        
        messages.success(request,f'job #{job_data['job_id']} added')
        # Remove this item from session
        items = request.session.get('batch_jobs', [])
        

        items = [item for item in items if int(item['job_id']) != int(job_data['job_id'])]
        request.session['batch_jobs'] = items
        return redirect('jobs_batch_entry')


def fetch_api_data(request):
    url = "https://jsonplaceholder.typicode.com/posts"
    response = requests.get(url)
    data = response.json()  # Convert to dict
    return render(request, 'inventory/api_data.html',{'data':data})

def sync_engineers_view(request):
    try:
        sync_engineers_func(request)
    except:
        messages.error(request,"Syncing failed.")
        return redirect('admin_panel')
    messages.success(request,"Engineers synced.")
    return redirect('admin_panel')


def fetch_jobs(request,job_id=None):
    # try:
        with transaction.atomic():
            sync_engineers_func(request)
            headers = {"Authorization": f"Bearer {request.user.company.settings.sf_access_token }"}
            if job_id:
                print()
                # response = requests.get(f"https://api.servicefusion.com/v1/jobs/{job_id}", headers=headers) #for production
                response = requests.get(f"https://0350b95b-a46f-4716-94c8-b6677b1f904f.mock.pstmn.io/jobs/{job_id}", headers=headers) #for testing
                
            else:
                # response = requests.get("https://api.servicefusion.com/v1/jobs", headers=headers) #for production
                response = requests.get("https://0350b95b-a46f-4716-94c8-b6677b1f904f.mock.pstmn.io/jobs", headers=headers) #for testing

            # If token expired, refresh and retry
            if response.status_code == 401:
                new_token = refresh_sf_token(request.user.company)
                headers["Authorization"] = f"Bearer {new_token}"
                response = requests.get("https://api.servicefusion.com/v1/jobs", headers=headers)
            data = response.json()
            field_map={
                'status':lambda d:d["status"],
                "address":lambda d:f"{d['street_1']} {d.get('street_2', '')} {d['city']} {d['state_prov']} {d['postal_code']}",
                "parent_account":lambda d:d["parent_customer"],     
                "post_code":lambda d:d["postal_code"],  
                'date': lambda d: datetime.strptime(d["visits"][0]["start_date"], "%Y-%m-%d").date(),
                'birthday': lambda d: datetime.fromisoformat(d["created_at"]),
                'from_time': lambda d: datetime.strptime(d["visits"][0]["time_frame_promised_start"], "%H:%M").time(),
                'to_time': lambda d: datetime.strptime(d["visits"][0]["time_frame_promised_end"], "%H:%M").time(),
                "engineer":lambda d:Engineer.objects.get(Q(company=request.user.company) & Q(sf_id=d["visits"][0]["techs_assigned"][0]["id"])),
                "sf_id":lambda d:int(d["id"]),
                'comments':lambda d:d["notes"][0]

                
                    }
            if job_id:
                if int(data["id"]):
                    engineer=Engineer.objects.get(Q(company=request.user.company) & Q(sf_id=data["visits"][0]["techs_assigned"][0]["id"]))
                    
                    ex_job=Job.objects.get(Q(company=request.user.company) & Q(job_id=job_id))
                    update_if_changed(ex_job, data, field_map,request=request, affected_by_sync=True, )
                    messages.success(request,f"Job with id {data['number']} synced successfully")
                    return redirect('update_job',job_id)
            else:      
                updated_count=0
                new_count=0  
                for d in data["items"]:
                    print("sssssssssssssssssssssss",d["notes"][0]["notes"])

                    if int(d["id"]):
                        engineer=Engineer.objects.get(Q(company=request.user.company) & Q(sf_id=d["visits"][0]["techs_assigned"][0]["id"]))
                        try:
                            
                            ex_job=Job.objects.get(Q(company=request.user.company) & Q(job_id=d["number"]))
                            x=update_if_changed(ex_job, d, field_map,request=request, affected_by_sync=True, )
                            updated_count=updated_count+1 if len( x ) > 0 else updated_count
                    
                            # ex_job.address = f"{d['street_1']} {d.get('street_2', '')} {d['city']} {d['state_prov']} {d['postal_code']}"
                            # ex_job.parent_account=d["parent_customer"]
                            # ex_job.post_code=d["postal_code"]
                            # ex_job.date=d["visits"][0]["start_date"]
                            # ex_job.from_time=d["visits"][0]["time_frame_promised_start"]
                            # ex_job.to_time=d["visits"][0]["time_frame_promised_end"]
                            # ex_job.birthday=d["created_at"]
                            # ex_job.engineer=engineer
                            # ex_job.save(update_fields=['address','parent_account','post_code','date','from_time','to_time','birthday','engineer'],request=request,affected_by_sync=True)
                        except Job.DoesNotExist:
                            synced_job=Job(
                                company=request.user.company,
                                job_id=int(d["number"]),
                                address = f"{d['street_1']} {d.get('street_2', '')} {d['city']} {d['state_prov']} {d['postal_code']}",
                                status= d["status"],
                                quotation=None,
                                engineer=engineer,#Temporarily nnon
                                parent_account=d["parent_customer"],
                                added_date=timezone.now(),
                                items_arrived=False,
                                post_code=d["postal_code"],
                                quoted=False,
                                quote_accepted=False,
                                quote_declined=False,
                                date=d["visits"][0]["start_date"],
                                from_time=d["visits"][0]["time_frame_promised_start"],
                                to_time=d["visits"][0]["time_frame_promised_start"],
                                # history =None ,
                                # comments = None,
                                birthday=d["created_at"],
                                retirement_date=None,
                                on_hold=False,
                                parts_need_attention=True if d["status"] == "paused" else False,
                                added_by_sync=True,
                                sf_id=int(d["id"]),
                            )   
                            synced_job.save(request=request,affected_by_sync=True)
                            new_count=new_count+1

                messages.success(request,f"{new_count}Jobs synced successfully.")
                messages.success(request,f"{updated_count}Jobs updated successfully.")

                           
            #data = data.get("items", [])# Convert to dict
            
            return redirect("inventory")
    # except:
    #     messages.error(request,"Synicng failed")
    #     return redirect("inventory")
    

def scheduler(request):
    
    import socket
    try:
        # Try to connect to a well-known DNS (Google)
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        internet_ok = True
    except OSError:
        internet_ok = False

    if not internet_ok:
        messages.error(request,"Internet issue")
        # return redirect("scheduler")
    ex_sg = SchedulerGroup.objects.filter(
        company=request.user.company,
        user=request.user,
        wrong_postcodes=False,
        

    ).annotate(job_count=Count("jobs")).order_by("-job_count")

    groupx = SchedulerGroup.objects.filter(
        company=request.user.company,
        user=request.user,
        wrong_postcodes=True
    ).first()   

    # Safe handling
  
    if  (request.POST and "regenerate" in request.POST):
        
        if ex_sg.exists():
            ex_sg.exclude(scheduler=True).delete()

        if groupx:  # check it’s not None before calling delete
            groupx.delete()

   
    # --- Helper: get coordinates from postcode ---
        # --- Step 1: Fetch all ready jobs ---
        base_jobs = Job.objects.filter(company=request.user.company,status="ready",)
        ready_jobs=list(base_jobs.exclude(scheduler=request.user))
        
        if not ready_jobs:

            return redirect ("scheduler")
        # --- Step 2: Cache postcode coordinates ---
        for job in ready_jobs:
            if not job.latitude or not job.longitude:
                try:
                    postcode = job.post_code.strip().upper().replace(" ", "")   
                    job.latitude, job.longitude = get_coords(postcode)  
                except:
                    job.latitude, job.longitude=None,None
                    pass
            # --- Step 3: Grouping Logic ---
        visited = set()
        wrong_list=[]
        for job in ready_jobs:
            if job.id in visited:
                continue
            
            if job.latitude and job.longitude:
                jobs_list=[]
                jobs_list.append(job)
                visited.add(job.id)
                distances = []
                for other in ready_jobs:
                    if other.id in visited or not other.latitude:
                        continue     
                    d = haversine(job.latitude, job.longitude, other.latitude, other.longitude)
                    distances.append({"other": other, "distance": d})

                    distances.sort(key=lambda x: x["distance"])

                # Step 3: pick closest ones up to limit
                for entry in distances:
                    other = entry["other"]
                    distance = entry["distance"]

                    if (distance <= 15    and len(jobs_list) < 9) or (
                        job.post_code.strip() == other.post_code.strip()
                    ):
                        jobs_list.append(other)
                        visited.add(other.id)
                postcodes = [j.post_code.strip().upper().replace(" ", "") for j in jobs_list if j.post_code]
                map_url = "https://www.google.com/maps/dir/" + "/".join(postcodes)
                group_obj = SchedulerGroup.objects.create(
                company=request.user.company,
                user=request.user,
                map_url=map_url,

                
                )
                group_obj.jobs.set(jobs_list)
                group_obj.job_order=[job.id for job in jobs_list] 
                group_obj.save()
                
            else:
                if job.id in visited :
                    continue
             
                wrong_list.append(job)
                visited.add(job.id)
                for other in ready_jobs:
                    if other.id in visited or  other.latitude or other.longitude:
                        continue    
                    if not other.longitude and not other.latitude:
                        wrong_list.append(other)
                        visited.add(other.id)  
                
        if wrong_list:
            wrong_group_obj = SchedulerGroup.objects.create(
                company=request.user.company,
                user=request.user,
                map_url=None,
                wrong_postcodes=True,               
                )
            wrong_group_obj.jobs.set(wrong_list)
            wrong_group_obj.save()
        messages.success(request,"Groups regenerated")
        return redirect('scheduler')
    elif "optimize" in request.POST:
        # 🔄 Optimize every SchedulerGroup
        for group in ex_sg:
            if group.optimized_at:
                continue  # Skip already optimized groups   

            # Fetch related jobs
            jobs = list(group.ordered_jobs())
            
            # Attach coordinates (cached)
            for job in jobs:
                postcode = job.post_code.strip().upper().replace(" ", "") 
                job.latitude, job.longitude = get_coords(postcode)

            # Optimize order
            optimized_jobs = _greedy_fallback(jobs)
            # ✅ Update ManyToMany relation
            group.jobs.set(optimized_jobs, clear=True)
            group.job_order=[job.id for job in optimized_jobs] 
            # Generate map URL
            postcodes = [j.post_code.strip().upper().replace(" ", "") for j in optimized_jobs if j.post_code ]
            group.map_url = "https://www.google.com/maps/dir/" + "/".join(postcodes)
            print("Generated map URL:", group.map_url)
            # Mark optimization time
            group.optimized_at = timezone.now()
            # ✅ Save only normal fields (no M2M)
            group.save()
        return redirect('scheduler')
    
               
    elif request.method == "POST" and ("move_up" in request.POST or "move_down" in request.POST or "new_group" in request.POST ):
        
            try:
                    
                move(request,ex_sg)
                return redirect("scheduler")
                
            except:
                messages.error(request,"An error ocurried, try again ")
                return redirect("scheduler")
            #     pass
    elif   request.method == "POST" and('i_work_on_this' in request.POST):
        
        group_id=request.POST.get("i_work_on_this")
        i_work_on_this(request,group_id)
        return redirect("scheduler")
    elif request.method == "POST" and('i_donot_work_on_this' in request.POST):
        group_id=request.POST.get("group_id")
    
        i_donot_work_on_this(request,group_id)
        return redirect("scheduler")
    
        
    form = JobForm()
   
    
    if any(k in request.POST for k in ["change_from_date", "change_from_time", "change_to_time",]):
            
            job_id=request.POST.get("job_id")
            job=Job.objects.filter(company=request.user.company,id=job_id).first()
            date_str = request.POST.get("change_from_date",None)
            from_time_str = request.POST.get("change_from_time",None)  # corrected name
            to_time_str = request.POST.get("change_to_time",None)
            date_value = parse_date(date_str) if date_str else job.date
            from_time_value = parse_time(from_time_str) if from_time_str else job.from_time
            to_time_value = parse_time(to_time_str) if to_time_str else job.to_time
        
            data=model_to_dict(job)
            data["date"] = date_value.strftime("%Y-%m-%d") if date_value else None
            data["from_time"] = from_time_value.strftime("%H:%M:%S") if from_time_value else None
            data["to_time"] = to_time_value.strftime("%H:%M:%S") if to_time_value else None

            form = JobForm(data, instance=job)
            
            if form.is_valid():
                
                job = form.save(commit=False)
                
                job.save(update_fields=["date", "from_time", "to_time"], request=request)
              
                if 'date' in form.changed_data:
                    
                    messages.info(request,f"job {job.address} moved to {job.date} ")
                return redirect('scheduler') 
    elif "change_engineer" in request.POST:
        print("---------------",request.POST)
        eng_id=request.POST.get("change_engineer",None)
        group_id=request.POST.get("group_id")

        group=SchedulerGroup.objects.filter(company=request.user.company,user=request.user,id=group_id).first()

        if eng_id:
            
            eng=Engineer.objects.filter(company=request.user.company,id=eng_id).first()
        else :
            eng=None
        if group :
            print(group)
            group.engineer=eng
            group.save(update_fields=['engineer'])
            for j in group.jobs.all():
                print(j)
                j.engineer=eng
                print(j.engineer)
                j.save(update_fields=['engineer'])
        return redirect('scheduler') 
    elif "change_group_date" in request.POST:
        group_id=request.POST.get("group_id")

        group=SchedulerGroup.objects.filter(company=request.user.company,user=request.user,id=group_id).first()
        if group:
            date_str = request.POST.get("change_group_date",None)
            date_value = parse_date(date_str) if date_str else group.date
            job_example=group.jobs.all().first()
            data=model_to_dict(job_example)
            data["date"] = date_value.strftime("%Y-%m-%d") if date_value else None
            
            form = JobForm(data, instance=job_example)
            
            if form.is_valid():
                group.date=date_value
                group.save(update_fields=["date"])
                print("HEEEY",date_value)
                print("hey20", data['date'])
                for j in group.jobs.all():
                    j.date=date_value
                    j.save(update_fields=["date"])
            
        return redirect('scheduler') 

        
    other_jobs = Job.objects.filter(company=request.user.company,status="ready",latitude__isnull=False).exclude(scheduler=request.user).exclude(job_groups__in=ex_sg).distinct()
    # Get the first SchedulerGroup with no map_url
    return render(request, "inventory/scheduler.html", {"groups":  ex_sg,'ex_sg':ex_sg[0] if ex_sg else None ,'groupx':groupx,'other_jobs':other_jobs,'form':form,'form_job_id':form.instance.job_id})

#youssif_USF_SPY





# views.py
from calendar import monthrange, Calendar
from datetime import date, datetime, timedelta
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import Job  # adjust import as needed

@login_required
def monthly_calendar(request, year=None, month=None):
    # Defaults to current month
    today = timezone.localdate()
    if year and month:
        try:
            year = int(year); month = int(month)
            current = date(year, month, 1)
        except Exception:
            current = date(today.year, today.month, 1)
    else:
        current = date(today.year, today.month, 1)

    cal = Calendar(firstweekday=0)  # 0 = Monday? Python's 0 is Monday; change if needed
    month_days = list(cal.monthdatescalendar(current.year, current.month))
    # month_days is a list of weeks, each week is list of 7 date objects

    # Filter jobs for this company and month range
    user_company = getattr(request.user, 'company', None)
    if not user_company:
        jobs_qs = Job.objects.none()
    else:
        first_day = month_days[0][0]
        last_day = month_days[-1][-1]
        jobs_qs = Job.objects.filter(company=user_company, date__range=(first_day, last_day)).order_by('date', 'from_time')
        
    # Group jobs by date
    jobs_by_date = {}
    for job in jobs_qs:
        if job.date:
            jobs_by_date.setdefault(job.date, []).append(job) ####Need explanation waht is setdefault
   
    # Create prev/next month values
    prev_month = (current.replace(day=1) - timedelta(days=1)).replace(day=1)
    next_month = (current.replace(day=28) + timedelta(days=4)).replace(day=1)  # safe next-month calc
    prev_month_url = reverse('calendar_month', args=[prev_month.year, prev_month.month])
    next_month_url = reverse('calendar_month', args=[next_month.year, next_month.month])
    

    


    context = {
        'month_weeks': month_days,           # list of weeks -> each week is list of 7 date objects
        'current_month': current,
        'today': today,
        'jobs_by_date': jobs_by_date,
        'prev_month_url': prev_month_url,
        'next_month_url': next_month_url,
    }
    if request.method=='POST':
      
        if any(k in request.POST for k in ["change_from_date", "change_from_time", "change_to_time"]):            
            job_id=request.POST.get("job_id")
            job=jobs_qs.filter(job_id=job_id).first()
            date_str = request.POST.get("change_from_date",None)
            print("datestrr",date_str)
            from_time_str = request.POST.get("change_from_time",None)  # corrected name
            to_time_str = request.POST.get("change_to_time",None)
            date_value = parse_date(date_str) if date_str else job.date
            from_time_value = parse_time(from_time_str) if from_time_str else job.from_time
            to_time_value = parse_time(to_time_str) if to_time_str else job.to_time
           
            data=model_to_dict(job)
            data["date"] = date_value.strftime("%Y-%m-%d") if date_value else None
            data["from_time"] = from_time_value.strftime("%H:%M:%S") if from_time_value else None
            data["to_time"] = to_time_value.strftime("%H:%M:%S") if to_time_value else None

            form = JobForm(data, instance=job)
            
            if form.is_valid():
                job = form.save(commit=False)
                
                job.save(update_fields=["date", "from_time", "to_time"], request=request)
                print(form.changed_data)
                if 'date' in form.changed_data:
                    
                    messages.info(request,f"job {job.address} moved to {job.date} ")
                return redirect(request.path) 
            else:
                context["form"] = form
                context["form_job_id"] = form.instance.job_id
                return render(request, 'inventory/calendar.html', context)
            # context["form"]=form
            
        
    return render(request, 'inventory/calendar.html', context)

@login_required

def delete_all_jobs(request):
    from django.contrib.admin.utils import get_deleted_objects
    jobs = Job.objects.filter(company=request.user.company)
    count = jobs.count()

    for job in jobs:
        job.delete()   # committed immediately

    messages.success(request, f"{count} jobs deleted")
    return redirect("inventory")


@require_POST
def move_job_to_date(request):
    """
    AJAX endpoint: receives { job_id, target_date } and updates job.date to target_date.
    Returns JSON with updated job summary.
    """
    try:
        job_id = int(request.POST.get('job_id'))
        target = request.POST.get('target_date')  # expected YYYY-MM-DD
        target_date = datetime.strptime(target, "%Y-%m-%d").date()
    except Exception:
        return HttpResponseBadRequest("Invalid data")

    job = get_object_or_404(Job, pk=job_id, company=request.user.company)
    # Optionally clear times if you want
    job.date = target_date
    # If you want, keep existing times; otherwise uncomment:
    # job.from_time = None
    # job.to_time = None
    job.save()

    # minimal JSON summary for client update
    data = {
        'ok': True,
        'job_id': job.id,
        'new_date': job.date.isoformat(),
        'card_html': render_job_card_html(job, request)  # returns small html snippet server-side
    }
    return JsonResponse(data)

# small helper to render the job card server-side (so client can insert if needed)
from django.template.loader import render_to_string
def render_job_card_html(job, request):
    return render_to_string('inventory/_job_card.html', {'job': job, 'request': request})
