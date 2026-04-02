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
    available = models.BooleanField(default=True)

      
    def __str__(self):
        return self.name
    
class Patients(models.Model):
    username = models.CharField(max_length=100)
    email = models.EmailField()
    password = models.CharField(max_length=100)
    
    phone = models.CharField(max_length=15, blank=True)
    city = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    profile_image = CloudinaryField('image', folder='patients_image')
    
    def __str__(self):
        return self.username


class Appointment(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Cancelled', 'Cancelled'),
    )
    
    PAYMENT_METHOD = (
        ('Cash', 'Cash'),
        ('Online', 'Online'),
    )
    
    user = models.ForeignKey(
        Patients, 
        on_delete=models.CASCADE, 
        related_name='appointments'   # ✅ IMPORTANT
    )
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD, default='Cash')
    
    is_billed = models.BooleanField(default=False)
     
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} -> {self.doctor.name} @ {self.appointment_date}"
   
class Billing(models.Model):
    PAYMENT_STATUS = (
        ('Paid', 'Paid'),
        ('Unpaid', 'Unpaid'),
    )

    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE)  # 🔥 IMPORTANT
    
    amount = models.FloatField()
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS, default='Unpaid')
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Bill #{self.id} - {self.appointment.user.username} - ₹{self.amount}"  
  

class Contact(models.Model):
    name = models.CharField(max_length=50)
    email = models.EmailField()
    subject = models.CharField(max_length=300)
    message = models.TextField()   # ✅ FIXED
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)  # ✅ FIXED

    def __str__(self):
        return self.name
    