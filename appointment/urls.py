from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('patient_programs/', views.patient_programs, name='patient_programs'),
    path('doctor/<str:category_name>/', views.doctor, name='doctor'),
    path('doctor_info/<int:id>/', views.doctor_info, name='doctor_info'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('my-profile/', views.my_profile, name='my_profile'),
    path('edit-profile/<int:id>/', views.edit_profile, name='edit_profile'),
    path('user_appointment/', views.user_appointment, name='user_appointment'),
    path('book_appointment/<int:doctor_id>/', views.book_appointment, name='book_appointment'),
    path('approved_appointment/<int:id>/', views.approved_appointment, name='approved_appointment'),
    path('cancel_appointment/<int:id>/', views.cancel_appointment, name='cancel_appointment'),
    # path('pay/<int:appointment_id>/', views.stripe_payment, name='stripe_payment'),
    path('stripe-payment/<int:appointment_id>/', views.stripe_payment, name='stripe_payment'),
    path('stripe-success/<int:appointment_id>/', views.stripe_success, name='stripe_success'),
   
    
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout_user/', views.logout_user, name='logout_user'),
    
    
    # Admin
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
    path('toggle-doctor/<int:id>/', views.toggle_doctor, name='toggle_doctor'),
    path('doctor-edit/<int:id>/', views.doctor_edit, name='doctor_edit'),
    path('doctor-delete/<int:id>/', views.doctor_delete, name='doctor_delete'),

]
