from django.contrib import admin
from .models import CustomUser , Company , Job,Item
# Register your model here.
class ItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'quantity', 'reference','status','added_date', 'updated_time')
    list_display_links = ('name', 'reference')
    list_editable=[ 'status']
    list_filter = ('status',)
    search_fields = ('name', 'reference')
    #fields=[('name', )] #in case you need to show specific fields
# class CustomUserAdmin(admin.ModelAdmin):
#     list_display = ('username', 'email','is_staff' )

# admin.site.register(Job, )
admin.site.register(Item, )
# admin.site.register(JobItem, )
# admin.site.register(CustomUser,CustomUserAdmin)
# admin.site.site_header='Stock'
# admin.site.site_title='Stock'


admin.site.register(Job,  )
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email','is_staff','company','company__owner')   
    
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

