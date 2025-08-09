from django.contrib import admin
from .models import CustomUser , Company , Job,Item,Comment,JobItem,WarehouseItem,Engineer,category,CompanySettings,Email
# Register your model here.
class ItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', )
    list_display_links = ('name', )
    search_fields = ('name',)
    #fields=[('name', )] #in case you need to show specific fields
# class CustomUserAdmin(admin.ModelAdmin):
#     list_display = ('username', 'email','is_staff' )

# admin.site.register(Job, )
admin.site.register(Item, ItemAdmin)
admin.site.register(Engineer, )
admin.site.register(category, )
# admin.site.register(JobItem, )
# admin.site.register(CustomUser,CustomUserAdmin)
# admin.site.site_header='Stock'
# admin.site.site_title='Stock'
class JobItemAdmin(admin.ModelAdmin):

    list_display = ('id', 'item__part_number')
class WarehouseItemAdmin(admin.ModelAdmin):
    list_display = ('item','id',  )
admin.site.register(JobItem,JobItemAdmin)
admin.site.register(WarehouseItem,WarehouseItemAdmin)
    
admin.site.register(Job,  )
admin.site.register(Email,  )
admin.site.register(CompanySettings,  )


# @admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('content_object', 'comment', 'added_date', 'added_by',"content_type","id")
admin.site.register(Comment, CommentAdmin )
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email','is_staff','company','company__owner','password')   
    
admin.site.register(CustomUser, CustomUserAdmin )
class CompanyAdmin(admin.ModelAdmin): 
    list_display = ('company_name','company_email','owner' ,'owner__email',)
    
    def owner_email(self, obj):
        return obj.owner.email
    owner_email.short_description = 'Owner Email'

    def list_employees(self, obj):
        # Displaying the usernames of employees for the current company
        return ", ".join([user.username for user in obj.employees.all()])
    list_employees.short_description = 'Employees'
admin.site.register(Company,CompanyAdmin )

