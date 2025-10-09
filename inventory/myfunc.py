from django.db import models
def items_arrived(self):
    from .models import Job, JobItem
    all_arrived=False
    if self.pk:
        if isinstance(self,Job) and self.items.all().count()>0:
            all_arrived = all(
                    item.arrived or item.from_warehouse
                    for item in self.items.all()
                )
            
            self.items_arrived=all_arrived 
        elif isinstance(self,Job) :
            all_arrived=True
            self.items_arrived=all_arrived 
        elif isinstance(self,JobItem):
            all_arrived = all(
                    item.arrived or item.from_warehouse
                    for item in self.job.items.all()
                )
    return all_arrived

def items_not_used(self):
    from .models import Job, JobItem
    not_used=False
    if self.pk:
        if isinstance(self,Job) and self.items.all().count()>0:
            not_used = all(
                    not item.is_used
                    for item in self.items.all()
                )
            self.items_arrived=not_used 
        elif isinstance(self,Job) :
            not_used=True
            self.items_arrived=not_used 
        elif isinstance(self,JobItem):
            not_used = all(
                    not item.is_used
                    for item in self.job.items.all()
                )
    return not_used



def job_reopened(self,):
    if self.pk:
        old_instance = type(self).objects.get(pk=self.pk)
        old_status = old_instance.status
        if (self.status != "completed" and old_status == "completed" and self.status != "cancelled") or (self.status != "cancelled" and old_status == "cancelled" and self.status != "completed") :
                for item in self.items.all():
                    if item.is_used:
                        item.was_it_used=True
                        item.save(update_fields=['was_it_used'],no_recursion=True,request=None)
                return True
        return False
def quote_accepted(self,):
    if self.pk:
        if self.quoted:
            if self.quote_accepted:
                return True
            return False
        return True
    return False
def item_arrived(self):
    if self.from_warehouse:
        
        return True
    if self.ordered:
            if self.arrived_quantity >= self.job_quantity:
                self.arrived = True
            else:
                self.arrived=False
    else:
        self.arrived = False
    return self.arrived
def item_not_used(self):
    return self.is_used
def job_completed(self,):
    if self.status=='completed':
        for item in self.items.all():
            item.is_used=True
            item.save(update_fields=['is_used'],no_recursion=True,request=None)
        
        return True
    return False


def generate_otp():
    import random
    import string
    code = ''.join(random.choices(string.ascii_uppercase  + string.digits, k=6))
    # if user:
    #     user.otp=code
    #     user.save(update_fields=['otp'])
    return code
def send_otp_email(email, otp):
    from django.core.mail import send_mail
    from django.conf import settings
    send_mail(
        subject='Your OTP Code',
        message=f'Your OTP code is {otp}',
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=False,
    )
def send_guest_email(email, login_email,password):
    from django.core.mail import send_mail
    from django.conf import settings
    send_mail(
        subject='Stocky login credentials',
        message=f'Welcome to Stock, \n Your login details \n Email: {login_email} \n Password: {password} ',
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=False,
    )
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from collections import defaultdict
from django.utils import timezone
def send_multiple_emails(jobs, request=None,single=False,):
    
    # Group jobs by engineer
    engineer_jobs = defaultdict(list)
    for job in jobs:
        if job.engineer:
            engineer_jobs[job.engineer].append(job)

    # Send one email to each engineer
    for engineer, jobs_list in engineer_jobs.items():
        message_lines = [f"Hi {engineer.name}, please take the following parts for :\n"]
        
        for job in jobs_list:
            parts = [str(part)+str(("("+"x"+str(part.job_quantity)+")")) for part in job.items.all()]
            if parts:
                parts_text = ", ".join(parts)
            else:
                parts_text = "No parts assigned."
            message_lines.append(f"Job {job.address}:\n{parts_text}\n")

        full_message = "\n".join(message_lines)
        
        send_mail(
            subject=f"Your Job Parts List for{job.date}",
            message=full_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[engineer.email],  # Assumes `engineer.email` exists
            fail_silently=False,
        )
        from .models import Email
        user=request.user
        company=request.user.company
        if single:
            Email.objects.create(type=Email.EmailType.SINGLE,company=company,user=user,to=engineer.name,subject=f"Your Job Parts List for{job.date}",body=full_message,date=timezone.now(),)
        else:
            
            Email.objects.create(type=Email.EmailType.BATCH,company=company,user=user,to=engineer.name,subject=f"Your Job Parts List for{job.date}",body=full_message,date=timezone.now(),)



def update_if_changed(instance: models.Model, d: dict, field_map: dict, *,request=None, affected_by_sync=False, ignore_empty=False):
    """
    Update Django model instance only if one or more mapped fields differ from the new data.
    
    Args:
        instance: The Django model instance to update.
        data: Incoming data (from API, payload, etc.).
        field_map: Dict mapping model fields → callable(data) returning new value.
        request: Optional, passed to .save() if your model overrides save().
        afected_by_sync: Optional flag for custom save logic.
        ignore_empty: If True, ignores blank/None values from data.
    
    Returns:
        list: Names of changed fields (empty if no change).
    """
    changed_fields = []

    for field, get_val in field_map.items():
        try:
            # if field=="date" or field=="birthday":
            #     new_val = get_val(d).date()
            # elif field=="from_time" or field=="to_time":
            #     new_val = get_val(d).datetime()
            # else:
            new_val = get_val(d)
        except Exception as e:
            print(f"⚠️ Field '{field}' mapping failed: {e} --{new_val}")
            continue

        old_val = getattr(instance, field)

        # Optional cleanup for strings
        if isinstance(new_val, str):
            new_val = new_val.strip()
        if isinstance(old_val, str):
            old_val = old_val.strip()

        # Optionally skip empty values
        if ignore_empty and (new_val in ("", None)):
            continue

        # Compare & update
        if old_val != new_val:
            setattr(instance, field, new_val)
            changed_fields.append(field)

    # Save only if something actually changed
    if changed_fields:
        instance.save(
            update_fields=changed_fields,
            request=request,
            affected_by_sync=affected_by_sync
        )
        print(f"✅ {instance.__class__.__name__} {getattr(instance, 'id', '')} updated — {changed_fields}")
    else:
        print(f"⏩ {instance.__class__.__name__} {getattr(instance, 'id', '')} skipped — no changes detected.")

    return changed_fields
