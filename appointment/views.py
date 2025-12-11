from django.shortcuts import render, redirect, get_object_or_404
from .models import Doctor, Category, Appointment, Patients
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password


def index(request):
    doctors = Doctor.objects.all()[:10]
    return render(request, 'index.html', {'doctors': doctors, })


def doctor(request, category_name):
    if category_name == 'all doctor':
        doctors = Doctor.objects.all()
    else:
        doctors = Doctor.objects.filter(category__name=category_name)
        
    return render(request, 'doctor.html', {'doctors': doctors, 'category_name': category_name})


def doctor_info(request, id):
    doctor = Doctor.objects.get(id=id)
    releted_doctor = Doctor.objects.filter(category=doctor.category)[:10]
    
    return render(request, 'doctor_info.html', {'doctor': doctor, 'releted_doctor': releted_doctor})

def about(request):
    return render(request, 'about.html')

def contact(request):
    return render(request, 'contact.html')


def user_appointment(request):
    if 'login' in request.session:
        username = request.session['login']
        user = Patients.objects.get(username=username)
        appointments = Appointment.objects.filter(user=user)
        return render(request, 'user_appointment.html', {'appointments': appointments})
    else:
        messages.error(request, "Please login first!")
        return redirect('login')
    


# @login_required(login_url='login')
def book_appointment(request, doctor_id):
    # print(doctor_id)
    doctor = get_object_or_404(Doctor, id=doctor_id)
    # print(doctor)

    if 'login' in request.session:
        username = request.session['login']  
        user = Patients.objects.get(username=username)
        print(user)
        
        if request.method == 'POST':
            date = request.POST.get('date')
            time = request.POST.get('time')
            
            appointment = Appointment.objects.create(
                user = user,
                doctor = doctor,
                appointment_date = date,
                appointment_time = time,
                status='Pending'
            )
            
            send_mail(
                subject= 'Your Appointment is Confirmed',
                message=f"Dear {user.username}, \n\nYour appointment with {doctor.name} has been successfully booked on {date} at {time}",
                from_email= settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=False
            )
        
            messages.success(request, "Appointment Booked!")
            return redirect('user_appointment')
            # return render(request, 'user_appointment.html', {'appointments': appointments})
    else:
        messages.error(request, "Please Login Requered!")
        return redirect('login')
        
    return render(request, 'doctor_info.html', {'doctor': doctor,})


def approved_appointment(request, id):
    if 'login' in request.session:
        username = request.session['login']
        user = Patients.objects.get(username=username)

        appointment = get_object_or_404(Appointment, id=id, user=user)
        appointment.status = 'Approved'
        appointment.save()

        messages.success(request, "Appointment Complated Successfully!")
        return redirect(request.META.get('HTTP_REFERER'))
    else:
        messages.error(request, "Please login required!")
        return redirect('login')


def cancel_appointment(request, id):
    if 'login' in request.session:
        username = request.session['login']
        user = Patients.objects.get(username=username)

        appointment = get_object_or_404(Appointment, id=id, user=user)
        appointment.status = 'Cancelled'
        appointment.save()

        messages.success(request, "Appointment Cancelled Successfully!")
        return redirect(request.META.get('HTTP_REFERER'))
    else:
        messages.error(request, "Please login required!")
        return redirect('login')

  
def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # user = authenticate(request, username=username, password=password)
        patient = Patients.objects.filter(username=username).first()
        
        if patient is None:
            messages.error(request, "Username does not exist!")
            return redirect('login')
        
        
        if check_password(password, patient.password):
            messages.success(request, "Login Successfully!")
            request.session['login'] = username
            return redirect(index)
        else:
            messages.error(request, "Invalid Password!")
            return redirect('login')
    
    return render(request, 'login.html')


def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        
        if Patients.objects.filter(username=username).exists():
            messages.error(request, "Username Already Exists")
            return redirect(register)
            
        if Patients.objects.filter(email=email).exists():
            messages.error(request, 'Email Allerdy Exixst!')
            return redirect(register)
        
        hashed_pass = make_password(password)
        
        patient = Patients(username=username, email=email, password=hashed_pass)
        patient.save()
        
        messages.success(request, 'User Created Succefully!')
        return redirect(login)
        
    return render(request, 'register.html')


def logout_user(request):
    request.session.flush()
    messages.success(request, "Logout Succefully!")
    return redirect('home')





# admin

def dash_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_superuser or user.is_staff:
                auth_login(request, user)
                messages.success(request, "Admin Login Successfully!")
                return redirect(dash_admin)
            else:
                messages.error(request, "Access denied. Admins only.")
                return redirect(dash_login)
        
        doctor = Doctor.objects.filter(username=username).first();
        
        if doctor:
            if check_password(password, doctor.password):
                request.session['doctor_id'] = doctor.id
                messages.success(request, "Doctor Login Successfully")
                return redirect(doctor_dashboard)
            else:
                messages.error(request, "Invalid Password!")
                return redirect(dash_login)
            
        messages.error(request, "Invalid username or password")
        return redirect('dash_login')
    return render(request, 'dashboard/login.html')


def dash_logout(request):
    if 'doctor_id' in request.session:
        del request.session['doctor_id']

    if request.user.is_authenticated:
        logout(request)

    return redirect('dash_login')

@login_required(login_url=('/dash_login'))
def dash_admin(request):
    if request.user.is_superuser:
        total_doctors = Doctor.objects.count()
        appointment_total = Appointment.objects.count()
        total_patients = Patients.objects.count()
        latest_appointments = Appointment.objects.all().order_by('-created_at')[:10]

        return render(request, 'dashboard/index.html', {'action': 'admin', "role" : "admin", 'total_doctors': total_doctors, 'appointment_total': appointment_total, 'total_patients': total_patients, 'appointments': latest_appointments})
    
    return redirect(dash_login)

# @login_required(login_url=('/dash_login'))
def doctor_dashboard(request):
    doctor_id = request.session.get('doctor_id')
    if not doctor_id:
        return redirect(dash_login)
    
    doctor = Doctor.objects.get(id=doctor_id)
    
    appointments = Appointment.objects.filter(doctor=doctor).order_by('-created_at')
    total_appointments = appointments.count()
    total_patients = appointments.values('user').distinct().count()

    return render(request, 'dashboard/index.html', {"role" : "doctor", 'action': 'doctor', "doctor": doctor, "appointments": appointments, "total_appointments": total_appointments, "total_patients": total_patients})


def doctor_profile(request):
    doctor_id = request.session.get('doctor_id')
    doctor = Doctor.objects.get(id=doctor_id)
    return render(request, 'dashboard/doctor_profile.html', {"role" : "doctor", 'action': 'profile', 'doctor': doctor})

def edit_doctor(request):
    doctor_id = request.session.get('doctor_id')

    if not doctor_id:
        return redirect('dash_login')

    doctor = Doctor.objects.get(id=doctor_id)

    if request.method == "POST":
        doctor.name = request.POST.get('name')
        doctor.email = request.POST.get('email')
        doctor.degree = request.POST.get('degree')
        doctor.address = request.POST.get('address')
        doctor.experience = request.POST.get('experience')
        doctor.fees = request.POST.get('fees')
        doctor.about = request.POST.get('about')

        if request.FILES.get('image'):
            doctor.image = request.FILES.get('image')

        doctor.save()
        messages.success(request, "Profile Updated Successfully!")
        return redirect('edit_doctor')

    return render(request, "dashboard/edit_doctor.html", {
        "doctor": doctor,
        "action": "edit_doctor",
        "role": "doctor",
    })

def doctor_appointments(request):
    doctor_id = request.session.get('doctor_id')
  
    doctor = Doctor.objects.get(id=doctor_id)
    appointments = Appointment.objects.filter(doctor=doctor).order_by('-created_at')

    print(appointments)
    
    return render(request, 'dashboard/appointments.html', {'action': 'doctor_appointments',"role" : "doctor", 'appointments': appointments, "doctor": doctor})


@login_required(login_url=('/dash_login'))
@staff_member_required
def appointments(request):
    appointments = Appointment.objects.all()
    return render(request, 'dashboard/appointments.html', {'action': 'appointments',"role" : "admin", 'appointments': appointments})


@login_required(login_url=('/dash_login'))
@staff_member_required
def add_doctor(request):
    category = Category.objects.all()
    
    if request.method == "POST":
        image = request.FILES.get('image')
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        email = request.POST.get('email')
        degree = request.POST.get('degree')
        username = request.POST.get('username')
        password = request.POST.get('password')
        address = request.POST.get('address')
        experience = request.POST.get('experience')
        fees = request.POST.get('fees')
        about = request.POST.get('about')

        category = Category.objects.get(id=category_id) 
        
        pass_hashed = make_password(password)
             
        doctor = Doctor(image=image, name=name, email=email, username=username, password=pass_hashed, experience=experience, fees=fees, category=category, degree=degree, about=about, address=address)
        
        doctor.save()
        messages.success(request, "Doctor Added Succefully!")
        
        return redirect('add_doctor')
    
    return render(request, 'dashboard/add_doctor.html', {'category': category, "role" : "admin", 'action': 'add_doctor'})


@login_required(login_url=('/dash_login'))
@staff_member_required
def doctor_list(request):
    doctors = Doctor.objects.all()
    return render(request, 'dashboard/doctor_list.html', {'doctors': doctors, 'action': 'doctor_list', "role" : "admin"})

