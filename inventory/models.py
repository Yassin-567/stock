from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError

from django.contrib.auth.models import BaseUserManager, Group
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        
        user.save(using=self._db)

        # Ensure the user has at least one group.
        if not user.groups.exists():
            default_group, _ = Group.objects.get_or_create(name='Default')
            user.groups.add(default_group)

        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        user = self.create_user(email, password, **extra_fields)
        if not user.groups.exists():
            admin_group, _ = Group.objects.get_or_create(name='Admin')
            user.groups.add(admin_group)
        return user

class Company(models.Model):
    owner = models.ForeignKey("inventory.CustomUser", on_delete=models.CASCADE, null=True, blank=True,related_name="company_owner")
    employees = models.ManyToManyField('CustomUser', related_name='companies')
    company_name=models.CharField(max_length=70)
    company_email = models.EmailField(max_length=100)
    address=models.TextField()
    phone=models.CharField(max_length=15)
    def __str__(self):
        return self.company_name +" ("+ str(self.id)+") "
    
    class Meta:
        verbose_name_plural = 'companies'
        ordering = ['company_name']
    
class CustomUser(AbstractUser):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name="employeees")
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=90, unique=False)
    groups = models.ManyToManyField('auth.Group', related_name='users')
    REQUIRED_FIELDS = ['username',]
    USERNAME_FIELD = 'email'

    def __str__(self):
        return self.username +" ("+ str(self.id)+") "

    def save(self, *args, **kwargs):


        super().save(*args, **kwargs)
        # After saving, enforce that only one group is assigned:
        if self.pk and self.groups.count() > 1:
            first_group = self.groups.first()
            self.groups.set([first_group])

    class Meta:
        verbose_name_plural = 'users'
        ordering = ['id']
from django.db import models
################################## Items and Jobs ######################################

class Job(models.Model):
    status_chouces=[
        ('ready', 'Ready'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('quoted', 'Quoted and waiting')
    ]
    address = models.CharField(max_length=70)
    job_id=models.IntegerField()
    status=models.CharField(choices=status_chouces, max_length=20)
    parent_account=models.CharField(max_length=70)
    added_date=models.DateField(auto_now_add=True)
    company=models.ForeignKey(Company,on_delete=models.CASCADE,related_name="job_company")
    items_arrived=models.BooleanField(default=False, )
    post_code=models.CharField(max_length=10, null=True, blank=True)
    quoted=models.BooleanField(default=False)
    class Meta:
        unique_together = ('job_id', 'company')  # Enforce uniqueness at the company level

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.items_arrived=False #soublw check here
        if self.items.count() > 0:
            self.items_arrived =  not self.items.exclude(status="arrived").exists() 
        if self.status=="quoted":
            self.quoted=True
        if self.status == "completed":
            
            for item in self.items.all():
                
                if item.warehouse_quantity != 0:
                    item.warehouse_quantity = 0
                    item.is_used=True
                    item.status="arrived"
                    item.save()

        super().save(*args, **kwargs)
    def __str__(self):
        return self.address +" ("+ str(self.parent_account)+") "


class Comment(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)  # Reference to the model (Job or Item)
    object_id = models.PositiveIntegerField()  # ID of the related object
    company=models.ForeignKey(Company, on_delete=models.CASCADE,related_name="comment_company")
    content_object = GenericForeignKey('content_type', 'object_id','company')  # Generic relationship

    comment = models.TextField(null=True, blank=True)
    added_date = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING, null=False, blank=False, related_name="added_by")

    class Meta:
        ordering = ['-added_date']
    def __str__(self):
        return self.comment#[:20] + "..." if len(self.comment) > 20 else self.comment
    def save(self,*args, **kwargs):
        if not self.comment.strip():
            return
        super().save(*args, **kwargs) 
        
    

class Item(models.Model):
    CHOICES=[
        ('ordered', 'Ordered'),
        ('arrived', 'Arrived'),
        ('not_ordered','Not ordered'),
    ]
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="items"
    )    
    name=models.CharField(max_length=70)
    part_number=models.TextField(max_length=30)
    price=models.DecimalField(max_digits=10, decimal_places=2)
    supplier=models.CharField(max_length=70)
    status=models.CharField(max_length=20,choices=CHOICES,default="not_ordered")
    company=models.ForeignKey(Company,on_delete=models.CASCADE,related_name="item_company")
    added_date=models.DateTimeField(auto_now_add=True)
    added_by=models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING, null=True, blank=True, related_name="added_by_user")
    is_warehouse_item=models.BooleanField(default=False)
    warehouse_quantity=models.PositiveSmallIntegerField(default=0)
    job_quantity=models.PositiveSmallIntegerField(default=0)
    arrived_quantity=models.PositiveSmallIntegerField(default=0)
    is_used=models.BooleanField(default=False)
    def clean(self):
        if self.arrived_quantity > self.job_quantity:
            raise ValidationError("Arrived quantity cannot be greater than job quantity.")
        if self.warehouse_quantity > 0 and self.is_used:
            raise ValidationError("This item is used, you cannot change the warehouse quantity.")
    def save(self, *args, no_job=False,updating=True, **kwargs):
        if self.arrived_quantity > self.job_quantity:
            raise ValidationError("Arrived quantity cannot be greater than warehouse quantity.")
        if self.arrived_quantity==self.job_quantity:
            self.status = "arrived"
        else:
            self.status = "ordered"
        if not updating:
            if not no_job:
                print("HH")
                
                super().save(*args, **kwargs)
                self.job.save(*args, **kwargs)
                if self.job.status not in ["completed", "cancelled"]:   
                    if not self.job.items_arrived:
                        self.job.status = "paused"
                        self.job.save()
                    else:
                        self.job.status = "ready"
                        self.job.save()
            elif no_job:
                print("Hpp")
                self.is_warehouse_item=True
                super().save(*args, **kwargs)
        else:
            
            super().save(*args, **kwargs)
            self.job.save(*args, **kwargs)
            if self.job.status not in ["completed", "cancelled"]:   
                if not self.job.items_arrived:
                    self.job.status = "paused"
                    self.job.save()
                else:
                    self.job.status = "ready"
                    self.job.save()