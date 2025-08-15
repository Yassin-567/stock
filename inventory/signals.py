# your_app/signals.py

from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from .models import History

@receiver(pre_save)
def log_model_changes(sender, instance, **kwargs):
    
    # Avoid logging History model changes to prevent recursion
    if sender == History:
        return

    # Skip models without a company field (customize if needed)
    
    if not hasattr(instance, "company") :
        return

    # Only track existing objects (updates)
    
    if not instance.pk:
        return

    try:
        old_instance = sender.objects.get(pk=instance.pk)
        
    except sender.DoesNotExist:
        return  # Object doesn't exist yet, skip

    changed_fields = []
    old_values = []
    new_values = []
    allowed_fields=['']
    print("222",instance)
    for field in instance._meta.fields:
        print(field)
        field_name = field.name
        if field_name in allowed_fields:
            old_value = getattr(old_instance, field_name)
            new_value = getattr(instance, field_name)
            if old_value != new_value:
                changed_fields.append(field_name)
                old_values.append(str(old_value))
                new_values.append(str(new_value))

    if changed_fields:
        print(instance)
        user = getattr(instance, "_current_user", None)
        if not user:
            raise ValueError("No current user set on instance before saving!") 
        History.objects.create(
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.pk,
            company=instance.company,
            field=", ".join(changed_fields),
            old_value=", ".join(old_values),
            new_value=", ".join(new_values),
            user=getattr(instance, "_current_user", None)  # Set in views if you want
        )
