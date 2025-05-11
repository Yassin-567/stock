from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError

from django.contrib.auth.models import BaseUserManager, Group
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import F
#from datetime import datetime
#from time import strftime
############################---USER and COMPANY---############################
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
    groups = models.ManyToManyField('auth.Group', related_name='users',)
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

################################## Items, engineers and Jobs ######################################
class Engineer(models.Model):
    name=models.CharField(max_length=40,)
    email=models.EmailField()
    phone=models.CharField(max_length=15)
    company=models.ForeignKey(Company,on_delete=models.CASCADE,related_name="engineers_company",blank=True,null=True)

class Job(models.Model):
    status_chouces=[
        ('ready', 'Ready'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('quoted', 'Quoted and waiting')
    ]
    address = models.CharField(max_length=70)
    job_id=models.BigIntegerField()
    status=models.CharField(choices=status_chouces, max_length=20)
    engineer=models.ForeignKey(Engineer,on_delete=models.DO_NOTHING,null=True,blank=True)
    parent_account=models.CharField(max_length=70)
    added_date=models.DateField(auto_now_add=True)
    company=models.ForeignKey(Company,on_delete=models.CASCADE,related_name="job_company")
    items_arrived=models.BooleanField(default=False, )
    post_code=models.CharField(max_length=10, null=True, blank=True)
    quoted=models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('job_id', 'company')  # Enforce uniqueness at the company level

    def save(self, *args, **kwargs):
        old_status = None
        if self.pk:
            old_instance = type(self).objects.get(pk=self.pk)
            old_status = old_instance.status
        print("old status", old_status)
        super().save(*args, **kwargs)
        self.items_arrived=False #soublw check here
        if self.items.count() > 0:
            self.items_arrived =  not self.items.exclude(status="arrived").exists() 
        if self.status=="quoted":
            self.quoted=True
        if self.status == "completed":
            for item in self.items.all():
                if item.arrived_quantity != 0:
                    if item.job_quantity == item.arrived_quantity:
                        item.warehouse_quantity = 0
                        item.is_used=True
                    item.status="arrived"
                    item.save(no_recursion=True)
            
        elif self.status != "completed" and old_status == "completed" and self.status != "cancelled":
            for item in self.items.all():
                if item.is_used:
                    print("item is used")
                    item.notes='Job was completed then reopened, double check if the item was used.'
                    item.save(no_recursion=True) 
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
    
    name=models.CharField(max_length=70)
    part_number=models.TextField(max_length=30)
    reference=models.TextField(blank=True,null=True,max_length=40)
    price=models.DecimalField(max_digits=10, decimal_places=2)
    supplier=models.CharField(max_length=70)
    company=models.ForeignKey(Company,on_delete=models.CASCADE,related_name="item_company")
    added_date=models.DateTimeField(auto_now_add=True)
    added_by=models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING, null=True, blank=True, related_name="added_by_user")
    #is_warehouse_item=models.BooleanField(default=False)
    #is_moved_to_warehouse=models.BooleanField(default=False)
    #warehouse_quantity=models.PositiveSmallIntegerField(default=0)
    #job_quantity=models.PositiveSmallIntegerField(default=0)
    #arrived_quantity=models.PositiveSmallIntegerField(default=0)
    required_quantity=models.PositiveSmallIntegerField(default=0)
    arrived_quantity=models.PositiveSmallIntegerField(default=0)
    #status=models.CharField(max_length=20,choices=CHOICES,default="not_ordered")
    notes=models.TextField(null=True, blank=True)
    def __str__(self):
        return self.name

class JobItem(models.Model):
    CHOICES=[
        ('ordered', 'Ordered'),
        ('arrived', 'Arrived'),
        ('not_ordered','Not ordered'),
    ]
    job = models.ForeignKey(Job, on_delete=models.DO_NOTHING, related_name="items")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="job_items")
    job_quantity = models.PositiveSmallIntegerField(default=0)  # How many needed for this job
    arrived_quantity=models.PositiveSmallIntegerField(default=0)
    status=models.CharField(max_length=20,choices=CHOICES,default="not_ordered")
    is_used=models.BooleanField(default=False)
    from_warehouse=models.BooleanField(default=False)
    def __str__(self):
        return str(self.item.name)
class WarehouseItem(models.Model):
    CHOICES=[
        ('ordered', 'Ordered'),
        ('arrived', 'Arrived'),
        ('not_ordered','Not ordered'),
    ]
    company=models.ForeignKey(Company,on_delete=models.CASCADE,related_name="warehouse_company_items")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="warehouse_items")
    warehouse_quantity = models.PositiveSmallIntegerField(default=0)  
    status=models.CharField(max_length=20,choices=CHOICES,default="not_ordered")
    is_used=models.BooleanField(default=False)
    is_moved_from_job=models.BooleanField(default=False)

    def __str__(self):
        return str(self.item.name)