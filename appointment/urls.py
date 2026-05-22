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
    path('stripe-payment/<int:appointment_id>/', views.stripe_payment, name='stripe_payment'),
    path('stripe-success/<int:appointment_id>/', views.stripe_success, name='stripe_success'),
    path('add_comment/<int:doctor_id>/', views.add_comment, name='add_comment'),
    
   
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout_user/', views.logout_user, name='logout_user'),
    
    
    # Admin Panel Url
    path('dash_login/', views.dash_login, name='dash_login'),
    path('dash_logout/', views.dash_logout, name='dash_logout'),
    path('dash_admin/', views.dash_admin, name='dash_admin'),
    path('dash_admin/appointments/', views.appointments, name='appointments'),
    path('dash_admin/add_doctor/', views.add_doctor, name='add_doctor'),
    path('dash_admin/doctor_list/', views.doctor_list, name='doctor_list'),
    path('dash_admin/doctor_dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('dash_admin/doctor_appointments/', views.doctor_appointments, name='doctor_appointments'),
    path('dash_admin/doctor_profile/', views.doctor_profile, name='doctor_profile'),
    path('dash_admin/edit_doctor/', views.edit_doctor, name='edit_doctor'),
    path('dash_admin/toggle-doctor/<int:id>/', views.toggle_doctor, name='toggle_doctor'),
    path('dash_admin/doctor-edit/<int:id>/', views.doctor_edit, name='doctor_edit'),
    path('dash_admin/doctor-delete/<int:id>/', views.doctor_delete, name='doctor_delete'),
    path('dash_admin/doctor/view/<int:id>/', views.doctor_view, name='doctor_view'),
    
    path('dash_admin/patient-list/', views.patient_list, name='patient_list'),
    path('dash_admin/patient/<int:id>/', views.patient_detail, name='patient_detail'),
    path('dash_admin/delete-patient/<int:id>/', views.delete_patient, name='delete_patient'),
    
    path('dash_admin/billing/', views.billing, name='billing'),
    path('dash_admin/bill/<int:id>/', views.billing_invoice, name='billing_invoice'),
    
    path('dash_admin/analytics/', views.analytics, name='analytics'),
    path('dash_admin/messages/', views.messages, name='messages'),
    path('dash_admin/del_message/<int:id>', views.del_message, name='del_message'),
    path('dash_admin/settings/', views.setting, name='settings'),
    
    
    path('dash_admin/feedback/', views.doctor_feedback, name='doctor_feedback'),
    path('dash_admin/approve-comment/<int:comment_id>/', views.approve_comment, name='approve_comment'),
    path('dash_admin/delete-comment/<int:comment_id>/', views.delete_comment, name='delete_comment'),
]
