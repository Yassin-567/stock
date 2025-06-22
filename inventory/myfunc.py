def item_save(self, dont_move_used=False):
    
    if self.job_quantity == self.arrived_quantity and self.ordered:
        self.status = 'arrived'
    elif self.ordered:
        self.status = None
    elif not self.ordered:
        self.status = None

    #self.save(update_fields=['status'])

    if not dont_move_used:
        for item in self.job.items.all():
            if item.status == 'arrived' or item.from_warehouse:
                self.job.items_arrived = True
                self.job.status = 'ready'
            else:
                self.job.items_arrived = False
                self.job.status = 'paused'
                break
        job_save(self=self.job,no_recursion=True)
    super(type(self), self).save()

def job_save(self, *args,no_recursion=False, **kwargs):
        old_status = None
        if self.pk:
            old_instance = type(self).objects.get(pk=self.pk)
            old_status = old_instance.status
       # super().save(*args, **kwargs)
        self.items_arrived=False 
        
        if self.items.count() > 0:
            for item in self.items.all():
                if item.status=='arrived' or item.from_warehouse:
                    self.items_arrived=True
            #self.items_arrived =  not self.items.exclude(status="arrived").exists() 
        
        if self.status=="quoted":
            self.quoted=True
        if self.status != "completed" and old_status == "completed" and self.status != "cancelled" and not no_recursion:
            
            for item in self.items.all():
                if item.is_used:
                
                    print("item is used")
                    item.notes='Job was completed then reopened, double check if the item still exists.'
                    item.save(update_fields=['notes'])
        # if self.items_arrived:
        #     self.status='ready'            
        if self.status=='completed' and not no_recursion :
            for item in self.items.all():
                item.is_used=True
                item.save(update_fields=['is_used'])
            self.status='completed'
        
        
        super(type(self), self).save(*args, **kwargs)
    
        