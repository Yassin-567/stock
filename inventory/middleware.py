# middleware.py
from django.utils import timezone
from .models import Company,Job

class GuestCleanupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        now = timezone.now()
        try :
            Company.objects.filter(is_guest=True, expiry_date__lt=now).delete()
        except:
            pass
        return self.get_response(request)
