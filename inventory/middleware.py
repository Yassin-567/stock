# middleware.py
from django.utils import timezone
from .models import Company,Job
from random import choice
from django.db import transaction


class GuestCleanupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        
        now = timezone.now()
        try :
            jobs=Job.objects.all()
            for j in jobs:
                j.post_code=j.post_code+" "
                j.save(update_fields=['post_code','latitude','longitude'])
            Company.objects.filter(is_guest=True, expiry_date__lt=now).delete()
        except:
            pass
        

        
#         postcodes = [
#     "SW1A 1AA", "SW1E 5DN", "SW3 5UZ", "SW5 9AX", "SW6 1HS",
#     "SW7 2AZ", "SW8 2LG", "SW9 9SL", "SW10 0SZ", "SW11 1AA"
# ]
#         ready_jobs = Job.objects.filter(company=request.user.company, status="ready")

#         for job in ready_jobs:
#             # Create a full copy without saving yet
#             job.pk = None  # tells Django to insert a new record
#             job.job_id = choice(range(1000, 9999))
#             job.post_code = choice(postcodes)

#             # ✅ Save without history or signals if you use such logic
#             try:
#                 job.save(request=request, dont_save_history=True)
#             except TypeError:
#                 # if your Job model doesn’t accept request param
#                 job.save()

        return self.get_response(request)
