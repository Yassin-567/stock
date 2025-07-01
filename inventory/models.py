from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError

from django.contrib.auth.models import BaseUserManager
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import F
from .myfunc import items_arrived,job_reopened,item_arrived,job_completed,items_not_used
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
        # if not user.groups.exists():
        #     default_group, _ = Group.objects.get_or_create(name='Employee')
        #     user.groups.add(default_group)

        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        user = self.create_user(email, password, **extra_fields)

        # if not user.groups.exists():
        #     admin_group, _ = Group.objects.get_or_create(name='Admin')
        #     user.groups.add(admin_group)
        return user


class Company(models.Model):
    owner = models.ForeignKey("inventory.CustomUser", on_delete=models.CASCADE, null=True, blank=True,related_name="company_owner")
    employees = models.ManyToManyField('CustomUser', related_name='companies')
    company_name=models.CharField(max_length=70)
    company_email = models.EmailField(unique=True)
    address=models.TextField()
    phone=models.CharField(max_length=15)
    def __str__(self):
        return self.company_name +" ("+ str(self.id)+") "
    
    class Meta:
        verbose_name_plural = 'companies'
        ordering = ['company_name']
    
class CustomUser(AbstractUser):
    permission_choices=[('admin','Admin'),
                        ('employee','Employee'),
                        ('owner','Owner')]
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name="employeees")
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=90, unique=False)
    permission = models.CharField(choices=permission_choices,default='employee')
    is_owner=models.BooleanField(default=False,)
    is_admin=models.BooleanField(default=False,)
    is_employee=models.BooleanField(default=False,)
    is_banned=models.BooleanField(default=False,)
    REQUIRED_FIELDS = ['username',]
    USERNAME_FIELD = 'email'
    verbose_name='User'
    def save(self,*args, **kwargs):
        if self.is_banned:
            self.is_admin=False
            self.is_employee=False
        elif self.permission=='admin':
            self.is_admin=True
            self.is_employee=False
        elif self.permission=='employee':
            self.is_admin=False
            self.is_employee=True
        else:
            self.is_admin=False
            self.is_employee=True
        super().save()
    def __str__(self):
        return self.username +" ("+ str(self.id)+") "
    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs)
    #     # After saving, enforce that only one group is assigned:
    #     if self.pk and self.groups.count() > 1:
    #         first_group = self.groups.first()
    #         self.groups.set([first_group])
    class Meta:
        verbose_name_plural = 'users'
        ordering = ['is_owner','is_admin','is_employee','is_banned']
################################## Items, engineers and Jobs ######################################
class Engineer(models.Model):
    name=models.CharField(max_length=40,)
    email=models.EmailField()
    phone=models.CharField(max_length=15)
    company=models.ForeignKey(Company,on_delete=models.CASCADE,related_name="engineers_company",blank=False,null=False)
    def __str__(self):
        return str( self.name)
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
    quotation=models.DecimalField(max_digits=10, decimal_places=2,blank=True,null=True)
    engineer=models.ForeignKey(Engineer,on_delete=models.SET_NULL,null=True,blank=True)
    parent_account=models.CharField(max_length=70)
    added_date=models.DateField(auto_now_add=True)
    company=models.ForeignKey(Company,on_delete=models.CASCADE,related_name="job_company")
    items_arrived=models.BooleanField(default=False, )
    post_code=models.CharField(max_length=10, null=True, blank=True)
    quoted=models.BooleanField(default=False)
    class Meta:
        unique_together = ('job_id', 'company')  # Enforce uniqueness at the company level
        ordering=['-added_date']

    def save(self,*args, **kwargs):
        job_reopened(self,)
        if not job_completed(self,) and  self.status!='cancelled':
            print('ppoo')
            self.status = 'ready' if items_arrived(self) and items_not_used(self) else 'paused'
            self.items_arrived=items_arrived(self) and items_not_used(self)
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
        
    
CHOICES=[
        
        ('arrived', 'Arrived'),
        (' ','')
        
    ]
class category(models.Model):
    category=models.CharField(max_length=40,unique=True)
    company=models.ForeignKey(Company,on_delete=models.CASCADE,related_name="category_company")
    def __str__(self):
        return self.category
class Item(models.Model):    
    name=models.CharField(max_length=70)
    part_number=models.TextField(max_length=30)
    price=models.DecimalField(max_digits=10, decimal_places=2,)
    reference=models.TextField(blank=True,null=True,max_length=40)

    supplier=models.CharField(max_length=70)
    company=models.ForeignKey(Company,on_delete=models.CASCADE,related_name="item_company")
    added_date=models.DateTimeField(auto_now_add=True)
    added_by=models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING, null=True, blank=True, related_name="added_by_user")
    required_quantity=models.PositiveSmallIntegerField(default=0)
    arrived_quantity=models.PositiveSmallIntegerField(default=0)
    ordered=models.BooleanField(default=False)
    category = models.ForeignKey(category, on_delete=models.CASCADE, related_name="item_category", null=True, blank=True)
    def save(self, *args, **kwargs):
        if not self.category and self.company.id:
            self.category, _ = category.objects.get_or_create(company=self.company, category='Others')
        super().save(*args, **kwargs)
    #notes=models.TextField(null=True, blank=True)
    def __str__(self):
        return self.name
class JobItem(models.Model):
    
    job = models.ForeignKey(Job, on_delete=models.DO_NOTHING, related_name="items")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="job_items")
    job_quantity = models.PositiveSmallIntegerField(default=0)  # How many needed for this job
    arrived_quantity=models.PositiveSmallIntegerField(default=0)
    reference=models.TextField(blank=True,null=True,max_length=40)
    #status=models.CharField(max_length=20,choices=CHOICES,blank=True,null=True,default=None)
    ordered=models.BooleanField(default=False)
    arrived=models.BooleanField(default=False)
    is_used=models.BooleanField(default=False)
    from_warehouse=models.BooleanField(default=False)
    notes=models.TextField(null=True, blank=True)
    was_for_job=models.ForeignKey(Job, on_delete=models.DO_NOTHING,null=True,blank=True, related_name="moveditems")
    category = models.ForeignKey(category, on_delete=models.CASCADE, related_name="jobitem_category", null=True, blank=True)

    def save(self,*args, dont_move_used=False,no_recursion=False,**kwargs):
        item_arrived(self)
        if not self.category and self.job.id:
            self.category, _ = category.objects.get_or_create(company=self.job.company, category='Others')

        super().save(*args, **kwargs)
        if not dont_move_used and not no_recursion:
            self.job.save(update_fields=['status','items_arrived'],)
            
    def __str__(self):
        return str(self.item.name)


class WarehouseItem(models.Model):

    company=models.ForeignKey(Company,on_delete=models.CASCADE,related_name="warehouse_company_items")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="warehouse_items")
    warehouse_quantity = models.PositiveSmallIntegerField(default=0)  
    reference=models.TextField(blank=True,null=True,max_length=40)
    is_used=models.BooleanField(default=False)
    is_moved_from_job=models.ForeignKey(Job, on_delete=models.DO_NOTHING,null=True,blank=True, related_name="warehousemoveditems")
    category = models.ForeignKey(category, on_delete=models.CASCADE, related_name="warehouse_category", null=True, blank=True)
    def save(self, *args, **kwargs):
        if not self.category and self.company.id:
            print("TTT")
            self.category, _ = category.objects.get_or_create(company=self.company, category='Others')
        
        super().save(*args, **kwargs)
        print(self.category)
    def __str__(self):
        return str(self.item.name)