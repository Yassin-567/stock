
    # "'''Job'''"
    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs)
    #     self.items_arrived=False #soublw check here
    #     if self.items.count() > 0:
    #         self.items_arrived =  not self.items.exclude(status="arrived").exists() 
    #     if self.status=="quoted":
    #         self.quoted=True
    #     if self.status == "completed":
            
    #         for item in self.items.all():
                
    #             if item.warehouse_quantity != 0:
    #                 item.warehouse_quantity = 0
    #                 item.is_used=True
    #                 item.status="arrived"
    #                 item.save()

    #     super().save(*args, **kwargs)
    # def __str__(self):
    #     return self.address +" ("+ str(self.parent_account)+") "

# '''Item'''
    # def save(self, *args, no_job=False,updating=True, **kwargs):
    #         if self.arrived_quantity > self.job_quantity:
    #             raise ValidationError("Arrived quantity cannot be greater than warehouse quantity.")
    #         if self.arrived_quantity==self.job_quantity:
    #             self.status = "arrived"
    #         else:
    #             self.status = "ordered"
    #         if not updating:
    #             if not no_job:
    #                 print("HH")
                    
    #                 super().save(*args, **kwargs)
    #                 self.job.save(*args, **kwargs)
    #                 if self.job.status not in ["completed", "cancelled"]:   
    #                     if not self.job.items_arrived:
    #                         self.job.status = "paused"
    #                         self.job.save()
    #                     else:
    #                         self.job.status = "ready"
    #                         self.job.save()
    #             elif no_job:
    #                 print("Hpp")
    #                 self.is_warehouse_item=True
    #                 super().save(*args, **kwargs)
    #         else:
                
    #             super().save(*args, **kwargs)
    #             self.job.save(*args, **kwargs)
    #             if self.job.status not in ["completed", "cancelled"]:   
    #                 if not self.job.items_arrived:
    #                     self.job.status = "paused"
    #                     self.job.save()
    #                 else:
    #                     self.job.status = "ready"
    #                     self.job.save()