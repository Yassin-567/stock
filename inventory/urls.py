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
    path('job/<int:pk>/',views.update_job,name='update_job'),
    path('item/<int:pk>/',views.update_item,name='update_item'),
    path('adpanel/<int:pk>/',views.update_user,name='update_user'),
    path('adpanelc/<int:pk>/',views.update_company,name='update_company'),
    path('login/',views.login_user,name='login'),
    path('logout/',views.logout_user,name='logout'),
    path('registerc/',views.register_company,name='register_company'),
    path('createjob/',views.job_create,name='create_job'),
    path('additem/<int:pk>/', views.item_add, name='item_add'),
    path('register/',views.register_user,name='register'),
    path('adpanel/',views.admin_panel,name='admin_panel'),
    path('api/',views.fetch_api_data,name='api_data'),
]