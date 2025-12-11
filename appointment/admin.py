from django.contrib import admin
from .models import Category, Doctor, Appointment, Patients

# Register your models here.
admin.site.register(Category)
admin.site.register(Doctor)
admin.site.register(Appointment)
admin.site.register(Patients)

