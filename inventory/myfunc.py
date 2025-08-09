
def items_arrived(self):
    from .models import Job, JobItem
    all_arrived=False
    if self.pk:
        print('all',all_arrived)
        if isinstance(self,Job) and self.items.all().count()>0:
            all_arrived = all(
                    item.arrived or item.from_warehouse
                    for item in self.items.all()
                )
            print('all',all_arrived)
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
        old_status = None
        old_instance = type(self).objects.get(pk=self.pk)
        old_status = old_instance.status
        if self.status != "completed" and old_status == "completed" and self.status != "cancelled" :
                for item in self.items.all():
                    if item.is_used:
                        item.notes='Job was completed then reopened, double check if the item still exists.'
                        item.save(update_fields=['notes'],no_recursion=True)
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
            item.save(update_fields=['is_used'],no_recursion=True)
        
        return True
    return False

import random


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

from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from collections import defaultdict
from django.utils import timezone
def send_multiple_emails(jobs, request=None,single=False,):
    print("OOOO")
    # Group jobs by engineer
    engineer_jobs = defaultdict(list)
    for job in jobs:
        if job.engineer:
            engineer_jobs[job.engineer].append(job)

    # Send one email to each engineer
    for engineer, jobs_list in engineer_jobs.items():
        message_lines = [f"Hi {engineer.name}, please take the following parts for :\n"]
        
        for job in jobs_list:
            parts = [str(part) for part in job.items.all()]
            if parts:
                parts_text = ", ".join(parts)
            else:
                parts_text = "No parts assigned."
            message_lines.append(f"Job {job.address}:\n{parts_text}\n")

        full_message = "\n".join(message_lines)
        print("P")
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
            Email.objects.create(type=Email.EmailType.SINGLE,company=company,user=user,to="yass",subject=f"Your Job Parts List for{job.date}",body=full_message,date=timezone.now(),)
        else:
            
            Email.objects.create(type=Email.EmailType.BATCH,company=company,user=user,to="yass",subject=f"Your Job Parts List for{job.date}",body=full_message,date=timezone.now(),)

        if request:
            messages.success(request, f'Email sent to {engineer.name}')
