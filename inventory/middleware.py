# middleware.py
from django.utils import timezone
from .models import Company

class GuestCleanupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        now = timezone.now()
        Company.objects.filter(is_guest=True, expiry_date__lt=now).delete()
        return self.get_response(request)
