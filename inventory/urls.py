"""
URL configuration for stock project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Araise NotImplementedErrord an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from . import views
urlpatterns=[
    path('',views.inventory,name='inventory'),
    path('<int:pk>',views.inventory,name='inventory'),
    path('search',views.search_view,name='search_view'),
    path('job/<int:pk>/',views.update_job,name='update_job'),
    path('job/<int:pk>/<int:cancel>',views.update_job,name='update_job'),
    path('item/<int:pk>/',views.update_item,name='update_item'),
    path('witem/<int:pk>/',views.update_warehouse_item,name='update_warehouse_item'),
    path('adpanel/<int:pk>/',views.update_user,name='update_user'),
    path('forgotpassword/',views.forgot_password,name='forgot_password'),
    path('companysettings/',views.company_settings,name='company_settings'),
    path('adpanelc//',views.update_company,name='update_company'),
    path('adpaneleng/',views.engineer,name='add_eng'),
    path('updateeng/<int:pk>',views.update_engineer,name='update_engineer'),
    path('scheduler/',views.scheduler,name='scheduler'),
    
   
    


    path('add_cat/',views.add_category,name='add_category'),
    path('batch_entry',views.batch_entry,name='batch_entry'),
    path('clear_batch',views.clear_batch,name='clear_batch'),
    path('create_batch_items/', views.create_batch_items, name='create_batch_items'),

    path('get_jobs_from_sf/', views.fetch_jobs, name='get_jobs_from_sf'),
    path('get_jobs_from_sf/<int:job_id>/', views.fetch_jobs, name='get_jobs_from_sf'),

    path('sync_engineers/', views.sync_engineers_view, name='sync_engineers'),
    path('login/',views.login_user,name='login'),
    path('logout/',views.logout_user,name='logout'),
    path('registerc/',views.register_company,name='register_company'),
    path('otp/',views.verify_otp,name='otp'),
    path('createjob/',views.job_create,name='create_job'),
    path('warehouse/',views.warehouse,name='warehouse'),
    path('revieworders/',views.review_ordered_items,name='review_ordered_items'),

    path('show-sent-emails/', views.show_sent_emails, name='show_sent_emails'),

    path('emails',views.emails_history,name='emails_history'),
    path('history',views.history,name='history'),
    path('additem/<str:no_job>', views.item_add, name='item_add'),
    path('add_warehouseitem/', views.add_warehouseitem, name='add_warehouseitem'),
    path('additem/<int:pk>/', views.item_add, name='item_add'),
    path('create_guest',views.create_guest_request,name='create_guest'),
    path('register/',views.register_user,name='register'),
    path('adpanel/',views.admin_panel,name='admin_panel'),
    path('api/',views.fetch_api_data,name='api_data'),

    path('calendar/', views.monthly_calendar, name='calendar_root'),
    path('calendar/<int:year>/<int:month>/', views.monthly_calendar, name='calendar_month'),
    path('calendar/move-job/', views.move_job_to_date, name='move_job_to_date'),
]