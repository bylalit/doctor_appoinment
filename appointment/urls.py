from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('doctor/<str:category_name>/', views.doctor, name='doctor'),
    path('doctor_info/<int:id>/', views.doctor_info, name='doctor_info'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('user_appointment/', views.user_appointment, name='user_appointment'),
    path('book_appointment/<int:doctor_id>/', views.book_appointment, name='book_appointment'),
    path('approved_appointment/<int:id>/', views.approved_appointment, name='approved_appointment'),
    path('cancel_appointment/<int:id>/', views.cancel_appointment, name='cancel_appointment'),
   
    
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout_user/', views.logout_user, name='logout_user'),
    
    
    # admin
    path('dash_login/', views.dash_login, name='dash_login'),
    path('dash_logout/', views.dash_logout, name='dash_logout'),
    path('dash_admin/', views.dash_admin, name='dash_admin'),
    path('appointments/', views.appointments, name='appointments'),
    path('add_doctor/', views.add_doctor, name='add_doctor'),
    path('doctor_list/', views.doctor_list, name='doctor_list'),
    path('doctor_dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor_appointments/', views.doctor_appointments, name='doctor_appointments'),
    path('doctor_profile/', views.doctor_profile, name='doctor_profile'),
    path('edit_doctor/', views.edit_doctor, name='edit_doctor'),

]
