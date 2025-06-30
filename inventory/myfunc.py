
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