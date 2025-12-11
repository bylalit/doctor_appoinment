from django.db import models
from cloudinary.models import CloudinaryField

# Create your models here.

class Category(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name
    

class Doctor(models.Model):
    # image = models.ImageField(upload_to='doctor_image')
    image = CloudinaryField('image', folder='doctor_image')
    name = models.CharField(max_length=100)
    email = models.EmailField()
    username = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=100)
    experience = models.IntegerField()
    fees = models.FloatField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    degree = models.CharField(max_length=50)
    about = models.TextField()
    address = models.TextField()
      
    def __str__(self):
        return self.name
    
class Patients(models.Model):
    username = models.CharField(max_length=100)
    email = models.EmailField()
    password = models.CharField(max_length=100)
    
    def __str__(self):
        return self.username


class Appointment(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Cancelled', 'Cancelled'),
    )
    
    user = models.ForeignKey(Patients, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} -> {self.doctor.name} @ {self.appointment_date}"
    
