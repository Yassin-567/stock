# your_app/signals.py

from django.db.models.signals import pre_save,post_save,post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from .models import History,Company,CustomUser,Job,Category,JobItem,WarehouseItem,Engineer
from django.contrib.sessions.models import Session
@receiver(pre_save)
def log_model_changes(sender, instance,**kwargs):
    
    # Avoid logging History model changes to prevent recursion
    if sender == Session:
        
        return
    if sender == History:
        return
    
    # Skip models without a company field (customize if needed)
    try:
        if instance.dont_save_history:
            return
    except:
        pass
    if not hasattr(instance, "company") :
        return

    # Only track existing objects (updates)
    try:
        x=instance.request
        x=instance.request.user
    except:
        return
    if not instance.pk:
        return
    

    try:
        old_instance = sender.objects.get(pk=instance.pk)
        
    except sender.DoesNotExist:
        return  # Object doesn't exist yet, skip
    
    changed_fields = []
    old_values = []
    new_values = []
    allowed_fields=['job_quantity','supplier','arrived_quantity','is_used','category','warehouse_quantity','reference','address','is_banned','is_employee','is_admin','is_owner','permission','username','phone','email','name','to_time','from_time','date','post_code','parent_account','engineer','quotation','status','job']
    for field in instance._meta.fields:
        
        field_name = field.name
        
        if field_name and (field_name in allowed_fields) :
            old_value = getattr(old_instance, field_name)
            new_value = getattr(instance, field_name)
            print('new',new_value,old_value)
            if old_value != new_value:
                changed_fields.append(field_name)
                old_values.append(str(old_value))
                new_values.append(str(new_value))
    
    try:
        changed_fields.remove("last_login")
    except:
        pass
    if changed_fields:
        
        user = instance.request.user#getattr(instance, "_current_user", None)
        if not user:
            raise ValueError("Failed to save history") 
        History.objects.create(
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.pk,
            company=instance.company,
            field=", ".join(changed_fields),
            old_value=", ".join(old_values),
            new_value=", ".join(new_values),
            user=user#getattr(instance, "_current_user", None)  # Set in views if you want
        )
@receiver(post_save)
def log_model_creation(sender, created,instance, **kwargs):
    """Track new objects (after save, when PK is available)."""
    allowed_models=[History,CustomUser,Job,Category,JobItem,Engineer,WarehouseItem,Company]
    if sender not in allowed_models :
        return
    if not created:
        return
    try:
        x=instance.request
        x=instance.request.user
    except:
        return
    
    # try:
    #     x=sender.objects.get(pk=instance.pk)
    #     created=False
    #     print('created2',created,x)
    #     return
    # except:
    #     created=True
    #     print('created',created)
    try:
        if instance.dont_save_history:
            return
    except:
        pass
    if sender==Company:
        user=instance.owner
    else :
        user=instance.request.user
    if  instance.request :
        History.objects.create(
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.pk,  # now PK is available
            company=getattr(instance, "company", instance),
            field="",
            old_value="",
            new_value="",
            user=user ,
            created=True
        )
@receiver(post_delete)
def log_model_deletion(sender, instance, **kwargs):
    
    allowed_models = [CustomUser, Job, Category, JobItem, WarehouseItem,Engineer, Company]
    if sender not in allowed_models:
        return
    
    try:
        user = instance.request.user
    except Exception:
        user = None
    
    if not user:
        return
    
    History.objects.create(
        content_type=ContentType.objects.get_for_model(instance),
        object_id=instance.pk,
        company=getattr(instance, "company", instance),
        field="__deleted__",
        old_value=str(instance),  # snapshot of what was deleted
        new_value="",
        user=user,
        created=False
    )




