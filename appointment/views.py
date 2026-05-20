from django.shortcuts import render, redirect, get_object_or_404
from .models import Doctor, Category, Appointment, Patients, Contact, Billing, Comment
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password, check_password
from django.core.paginator import Paginator
import stripe
from django.urls import reverse
import cloudinary
import cloudinary.uploader
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import ExtractWeekDay
from django.db.models import Count, Sum, Q, F
from datetime import timedelta

stripe.api_key = settings.STRIPE_SECRET_KEY


def index(request):
    doctors = Doctor.objects.filter(available=True).order_by('-id')[:10]
    return render(request, 'index.html', {'doctors': doctors, })

def patient_programs(request):
    return render(request, 'patient_programs.html')


def doctor(request, category_name):
    if category_name == 'all doctor':
        doctor_list = Doctor.objects.filter(available=True)
    else:
        doctor_list = Doctor.objects.filter(category__name=category_name, available=True)

    paginator = Paginator(doctor_list, 16)  

    page_number = request.GET.get('page')
    doctors = paginator.get_page(page_number)

    return render(request, 'doctor.html', {
        'doctors': doctors,
        'category_name': category_name
    })

def doctor_info(request, id):
    doctor = Doctor.objects.get(id=id, available=True)
    releted_doctor = Doctor.objects.filter(category=doctor.category, available=True)[:10]
    comments = Comment.objects.filter(doctor=doctor, is_approved=True).order_by('-created_at')
    return render(request, 'doctor_info.html', {'doctor': doctor, 'releted_doctor': releted_doctor, 'comments': comments})

def about(request):
    return render(request, 'about.html')

def contact(request):
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        
        Contact.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message
        )
        
        messages.success(request, "Message Sent Successfully ✅")
        
        return redirect('contact')
        
    return render(request, 'contact.html')


def user_appointment(request):
    if 'login' in request.session:

        email = request.session['login']
        user = Patients.objects.get(email=email)

        appointments = Appointment.objects.filter(user=user)

        # Payment message handle
        payment = request.GET.get('payment')

        if payment == "success":
            messages.success(request, "✅ Payment Successful!")
        elif payment == "cancel":
            messages.error(request, "❌ Payment Cancelled!")

        return render(request, 'user_appointment.html', {
            'appointments': appointments
        })

    else:
        messages.error(request, "Please login first!")
        return redirect('login')


def add_comment(request, doctor_id):
    if request.method == "POST":
        user_email = request.session.get('login')
        
        if not user_email:
            messages.error(request, "You must be logged in to post a review.")
            return redirect('login')

        comment_text = request.POST.get('comment_text')
        rating_value = request.POST.get('rating')
        
        doctor = get_object_or_404(Doctor, id=doctor_id)
            
        patient = Patients.objects.filter(email=user_email).first()

        if patient and comment_text and rating_value:
            try:
                Comment.objects.create(
                    doctor=doctor,
                    patient=patient,
                    text=comment_text,
                    rating=int(rating_value)
                )
                messages.success(request, "Your review has been posted!")
            except Exception as e:
                messages.error(request, f"Error saving review: {e}")
        else:
            messages.error(request, "Please provide both a rating and a comment.")

    # Redirect back to the doctor profile page (ensure 'id' matches your URL parameter)
    return redirect('doctor_info', id=doctor_id)  
    

def book_appointment(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)

    if 'login' in request.session:
        email = request.session['login']  
        user = Patients.objects.get(email=email)
        
        
        if not user:
            messages.error(request, "User not found")
            return redirect('login') 

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
            appointment.save()

            try:
                send_mail(
                    subject='Your Appointment is Confirmed',
                    message=f"Dear {user.username}, \n\nYour appointment with {doctor.name} has been successfully booked on {date} at {time}",
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[user.email],
                    fail_silently=False
                )
            except Exception as e:
                print("EMAIL ERROR:", e)
        
            messages.success(request, "Appointment Booked!")
            return redirect('user_appointment')
            
    else:
        messages.error(request, "Please Login Requered!")
        return redirect('login')
        
    return render(request, 'doctor_info.html', {'doctor': doctor,})



def approved_appointment(request, id):

    appointment = get_object_or_404(Appointment, id=id)

    if request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff):
        pass  # full access


    elif 'doctor_id' in request.session:
        doctor_id = request.session.get('doctor_id')

        if appointment.doctor.id != doctor_id:
            messages.error(request, "You are not allowed ❌")
            return redirect(request.META.get('HTTP_REFERER'))

    elif 'login' in request.session:
        try:
            email = request.session['login']
            user = Patients.objects.get(email=email)

            if appointment.user != user:
                messages.error(request, "You are not allowed ❌")
                return redirect(request.META.get('HTTP_REFERER'))

        except Patients.DoesNotExist:
            messages.error(request, "User not found ❌")
            return redirect('dash_login')

    else:
        messages.error(request, "Login required ❌")
        return redirect('dash_login')

    # Already approved check
    if appointment.status == 'Approved':
        messages.info(request, "Already Approved!")
        return redirect(request.META.get('HTTP_REFERER'))

    # Update status
    appointment.status = 'Approved'

    # Billing create
    if not appointment.is_billed:
        Billing.objects.create(
            appointment=appointment,
            amount=appointment.doctor.fees,
            payment_status="Paid"
        )
        appointment.is_billed = True

    appointment.save()

    messages.success(request, "Appointment Approved & Billing Generated ✅")

    return redirect(request.META.get('HTTP_REFERER'))

    

def cancel_appointment(request, id):

    appointment = get_object_or_404(Appointment, id=id)

    if request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff):
        pass  # full access


    elif 'doctor_id' in request.session:
        doctor_id = request.session.get('doctor_id')

        if appointment.doctor.id != doctor_id:
            messages.error(request, "You are not allowed ❌")
            return redirect(request.META.get('HTTP_REFERER'))

    elif 'login' in request.session:
        try:
            email = request.session['login']
            user = Patients.objects.get(email=email)

            if appointment.user != user:
                messages.error(request, "You are not allowed ❌")
                return redirect(request.META.get('HTTP_REFERER'))

        except Patients.DoesNotExist:
            messages.error(request, "User not found ❌")
            return redirect('dash_login')

    else:
        messages.error(request, "Login required ❌")
        return redirect('dash_login')

    # Already Cancelled check
    if appointment.status == 'Cancelled':
        messages.info(request, "Already Cancelled!")
        return redirect(request.META.get('HTTP_REFERER'))

    # Update status
    appointment.status = 'Cancelled'
    appointment.save()

    messages.success(request, "Appointment Cancelled Successfully ❌")

    return redirect(request.META.get('HTTP_REFERER'))
    
    

def stripe_payment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    base_url = request.build_absolute_uri(reverse('user_appointment'))
    amount = int(appointment.doctor.fees * 100)
    
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],

        line_items=[{
            'price_data': {
                'currency': 'inr',
                'product_data': {
                    'name': f'Doctor Appointment - {appointment.doctor.name}',
                },
                'unit_amount': amount,
            },
            'quantity': 1,
        }],

        mode='payment',

        success_url=request.build_absolute_uri(
            reverse('stripe_success', args=[appointment.id])
        ),
        cancel_url=base_url,
    )
    
    return redirect(session.url)

def stripe_success(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    # Payment successful hone par update
    appointment.payment_method = "Online"
    appointment.save()

    messages.success(request, "Payment successfully!")

    return redirect('user_appointment')


def my_profile(request):
    if 'login' in request.session:
        email = request.session['login']
        user = Patients.objects.get(email=email)

        return render(request, 'profile.html', {'user': user})
    else:
        return redirect('login')
    
def edit_profile(request, id):
    patient = get_object_or_404(Patients, id=id)

    if request.method == 'POST':
        patient.username = request.POST.get('username')
        patient.email = request.POST.get('email')
        patient.phone = request.POST.get('phone')
        patient.city = request.POST.get('city')
        patient.address = request.POST.get('address')

        new_image = request.FILES.get('image')

        if new_image:
            # delete old image from cloudinary
            if patient.profile_image:
                try:
                    cloudinary.uploader.destroy(patient.profile_image.public_id)
                except:
                    pass

            # assign new image
            patient.profile_image = new_image


        patient.save()
        messages.success(request, "Profile Updated succfully")

        return redirect('my_profile') 

    return render(request, 'edit_profile.html', {'patient': patient})



  
def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # user = authenticate(request, username=username, password=password)
        patient = Patients.objects.filter(email=email).first()
        
        if patient is None:
            messages.error(request, "Username does not exist!")
            return redirect('login')
        
        
        if check_password(password, patient.password):
            messages.success(request, "Login Successfully!")
            request.session['login'] = email
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
        phone = request.POST.get('phone')
        city = request.POST.get('city')
        address = request.POST.get('address')
        profile_image = request.FILES.get('image')

        # Check email
        if Patients.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
            return redirect('register')

        # Password hash
        hashed_pass = make_password(password)

        # Save user
        patient = Patients(
            username=username,
            email=email,
            password=hashed_pass,
            phone=phone,
            city=city,
            address=address,
            profile_image=profile_image
        )
        patient.save()

        messages.success(request, "User created successfully!")
        return redirect('login')

    return render(request, 'register.html')



def logout_user(request):
    request.session.flush()
    messages.success(request, "Logout Succefully!")
    return redirect('home')





# Admin Panel Views

def dash_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_superuser or user.is_staff:
                auth_login(request, user)
                request.session['username'] = user.username
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
        
        latest_appointments = Appointment.objects.select_related('doctor', 'user')\
                                .order_by('-created_at')[:10]

        today = timezone.now().date()  

        today_list = Appointment.objects.filter(
            appointment_date__year=today.year,
            appointment_date__month=today.month,
            appointment_date__day=today.day
        ).select_related('doctor', 'user').order_by('appointment_time')

        today_appointments = today_list.count()

        appointments_chart = (
            Appointment.objects
            .annotate(day=ExtractWeekDay('appointment_date'))
            .values('day')
            .annotate(total=Count('id'))
            .order_by('day')
        )

        days_map = {
            1: 'Sun', 2: 'Mon', 3: 'Tue',
            4: 'Wed', 5: 'Thu', 6: 'Fri', 7: 'Sat'
        }

        chart_labels = []
        chart_data = []

        for item in appointments_chart:
            chart_labels.append(days_map[item['day']])
            chart_data.append(item['total'])
            
        
        completed_appointments = Appointment.objects.filter(status='Approved').count()
        pending_appointments = Appointment.objects.filter(status='Pending').count()
        cancelled_appointments = Appointment.objects.filter(status='Cancelled').count()
        
        # 🔥 NEW: Total Revenue
        total_revenue = Billing.objects.filter(payment_status='Paid').aggregate(
            total=Sum('amount')
        )['total'] or 0

        return render(request, 'dashboard/index.html', {
            'action': 'admin',
            "role": "admin",

            # Stats
            'total_doctors': total_doctors,
            'appointment_total': appointment_total,
            'total_patients': total_patients,
            'total_revenue': total_revenue,

            # Appointments
            'appointments': latest_appointments,

            # Today
            'today_appointments': today_appointments,
            'today_list': today_list,

            # Chart
            'chart_labels': chart_labels,
            'chart_data': chart_data,

            # Extra Stats
            'completed_appointments': completed_appointments,
            'pending_appointments': pending_appointments,
            'cancelled_appointments': cancelled_appointments,
        })

    return redirect('dash_login')


def doctor_dashboard(request):
    doctor_id = request.session.get('doctor_id')
    
    if not doctor_id:
        return redirect('dash_login')
    
    doctor = Doctor.objects.get(id=doctor_id)

    # All Appointments of this doctor
    appointments = Appointment.objects.filter(doctor=doctor).order_by('-created_at')

    total_appointments = appointments.count()
    total_patients = appointments.values('user').distinct().count()

    # Today Data
    today = timezone.now().date()

    today_list = Appointment.objects.filter(
        doctor=doctor,
        appointment_date__year=today.year,
        appointment_date__month=today.month,
        appointment_date__day=today.day
    ).select_related('doctor', 'user').order_by('appointment_time')

    today_appointments = today_list.count()

    # Weekly Chart (Doctor specific)
    appointments_chart = (
        Appointment.objects
        .filter(doctor=doctor)
        .annotate(day=ExtractWeekDay('appointment_date'))
        .values('day')
        .annotate(total=Count('id'))
        .order_by('day')
    )

    days_map = {
        1: 'Sun', 2: 'Mon', 3: 'Tue',
        4: 'Wed', 5: 'Thu', 6: 'Fri', 7: 'Sat'
    }

    chart_labels = []
    chart_data = []

    for item in appointments_chart:
        chart_labels.append(days_map[item['day']])
        chart_data.append(item['total'])

    # Status Counts (Doctor specific)
    completed_appointments = appointments.filter(status='Approved').count()
    pending_appointments = appointments.filter(status='Pending').count()
    cancelled_appointments = appointments.filter(status='Cancelled').count()

    # Latest Appointments Top 10
    latest_appointments = appointments.select_related('user')[:10]
    
    # Revenue
    total_revenue = Billing.objects.filter(
        payment_status='Paid',
        appointment__doctor=doctor
    ).aggregate(total=Sum('amount'))['total'] or 0



    return render(request, 'dashboard/index.html', {
        "role": "doctor",
        "action": "doctor",

        "doctor": doctor,

        # Stats
        "total_appointments": total_appointments,
        "total_patients": total_patients,
        
        # Revenue
        "total_revenue": total_revenue,

        # Today
        "today_appointments": today_appointments,
        "today_list": today_list,

        # Appointments
        "appointments": latest_appointments,

        # Chart
        "chart_labels": chart_labels,
        "chart_data": chart_data,

        # Status
        "completed_appointments": completed_appointments,
        "pending_appointments": pending_appointments,
        "cancelled_appointments": cancelled_appointments,
    })


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

            if doctor.image:
                try:
                    cloudinary.uploader.destroy(doctor.image.public_id)
                except:
                    pass

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

    status = request.GET.get('status')

    if status and status != "All":
        appointments = appointments.filter(status=status)

    total_appointments = Appointment.objects.filter(doctor=doctor).count()
    completed_appointments = Appointment.objects.filter(doctor=doctor, status='Approved').count()
    pending_appointments = Appointment.objects.filter(doctor=doctor, status='Pending').count()
    cancelled_appointments = Appointment.objects.filter(doctor=doctor, status='Cancelled').count()


    paginator = Paginator(appointments, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'dashboard/appointments.html', {
        'action': 'doctor_appointments',
        'role': 'doctor',

        'appointments': page_obj,  
        'page_obj': page_obj,
        'doctor': doctor,

        'total_appointments': total_appointments,
        'completed_appointments': completed_appointments,
        'pending_appointments': pending_appointments,
        'cancelled_appointments': cancelled_appointments,

        'filter_status': status,  
    })


@login_required(login_url='/dash_login')
@staff_member_required
def appointments(request):

    appointments_list = Appointment.objects.all().order_by('-created_at')

    status = request.GET.get('status')

    if status and status != "All":
        appointments_list = appointments_list.filter(status=status)


    total_appointments = Appointment.objects.count()
    completed_appointments = Appointment.objects.filter(status='Approved').count()
    pending_appointments = Appointment.objects.filter(status='Pending').count()
    cancelled_appointments = Appointment.objects.filter(status='Cancelled').count()

    # Pagination
    paginator = Paginator(appointments_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'dashboard/appointments.html', {
        'appointments': page_obj,
        'page_obj': page_obj,

        'total_appointments': total_appointments,
        'completed_appointments': completed_appointments,
        'pending_appointments': pending_appointments,
        'cancelled_appointments': cancelled_appointments,

        'filter_status': status,  

        'action': 'appointments',
        "role": "admin"
    })


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



@login_required(login_url='/dash_login')
@staff_member_required
def doctor_list(request):

    filter_status = request.GET.get('status') 

    doctors = Doctor.objects.all().order_by('-id')

    # Filter Apply
    if filter_status == 'available':
        doctors = doctors.filter(available=True)
    elif filter_status == 'unavailable':
        doctors = doctors.filter(available=False)

    # Counts (Always total from ALL doctors)
    total_doctor = Doctor.objects.count()
    available_doctor = Doctor.objects.filter(available=True).count()
    unavailable_doctor = Doctor.objects.filter(available=False).count()

    # Pagination
    paginator = Paginator(doctors, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'dashboard/doctor_list.html', {
        'doctors': page_obj,
        'page_obj': page_obj,
        'total_doctor': total_doctor,
        'available_doctor': available_doctor,
        'unavailable_doctor': unavailable_doctor,
        'filter_status': filter_status,  
        'action': 'doctor_list',
        "role": "admin"
    })


@login_required(login_url=('/dash_login'))
@staff_member_required
def doctor_view(request, id):
    doctor = get_object_or_404(Doctor, id=id)

    return render(request, 'dashboard/doctor_view.html', {
        'doctor': doctor,
        'action': 'doctor_list',
        "role": "admin"
    })
    
    
@login_required(login_url=('/dash_login'))
@staff_member_required
def doctor_edit(request, id):

    doctor = Doctor.objects.get(id=id)

    if request.method == "POST":
        doctor.name = request.POST.get('name')
        doctor.email = request.POST.get('email')
        doctor.degree = request.POST.get('degree')
        doctor.address = request.POST.get('address')
        doctor.experience = request.POST.get('experience')
        doctor.fees = request.POST.get('fees')
        doctor.about = request.POST.get('about')


        if request.FILES.get('image'):

            if doctor.image:
                try:
                    cloudinary.uploader.destroy(doctor.image.public_id)
                except:
                    pass

            doctor.image = request.FILES.get('image')
        doctor.save()

        messages.success(request, "Profile Updated Successfully!")
        return redirect('doctor_list')

    return render(request, "dashboard/admin_doc_edit.html", {
        "doctor": doctor,
        "action": "doctor_list",
        "role": "admin",
    })


@login_required(login_url=('/dash_login'))
@staff_member_required
def doctor_delete(request, id):

    doctor = get_object_or_404(Doctor, id=id)

    # Cloudinary Image Delete
    if doctor.image:
        try:
            cloudinary.uploader.destroy(doctor.image.public_id)
        except Exception as e:
            print("Image delete error:", e)

    # Doctor Delete
    doctor.delete()

    return redirect('doctor_list')

@login_required(login_url=('/dash_login'))
@staff_member_required
def toggle_doctor(request, id):
    doctor = get_object_or_404(Doctor, id=id)

    if request.method == "POST":
        doctor.available = 'available' in request.POST
        doctor.save()

    return redirect('doctor_list')


@login_required(login_url='/dash_login')
@staff_member_required
def patient_list(request):

    patients = Patients.objects.all()

    patients = patients.annotate(
        total_appointments=Count('appointments'),  
        total_bill=Sum(
            'appointments__doctor__fees',
            filter=Q(appointments__status='Approved')
        )
    ).order_by('-id')
    
    context = {
        'patients': patients,
        'action': 'patient_list',
        "role": "admin"
    }

    return render(request, 'dashboard/patient_list.html', context)


@login_required(login_url='/dash_login')
@staff_member_required
def patient_detail(request, id):

    patient = get_object_or_404(Patients, id=id)

    stats = Appointment.objects.filter(user=patient).aggregate(
        total_appointments=Count('id'),
        total_bill=Sum('doctor__fees', filter=Q(status='Approved')),
        pending=Count('id', filter=Q(status='Pending')),
        cancelled=Count('id', filter=Q(status='Cancelled')),
    )

    appointments = Appointment.objects.filter(user=patient).order_by('-created_at')

    context = {
        'patient': patient,
        'appointments': appointments,
        'stats': stats,
        'action': 'patient_list',
        "role": "admin"
    }

    return render(request, 'dashboard/patient_detail.html', context)


@login_required(login_url=('/dash_login'))
@staff_member_required
def delete_patient(request, id):
    if request.method == "POST":
        patient = get_object_or_404(Patients, id=id)
        patient.delete()
    return redirect('patient_list')


@login_required(login_url='/dash_login')
@staff_member_required
def billing(request):
    
    bills = Billing.objects.select_related(
        'appointment__user', 
        'appointment__doctor'
    ).order_by('-created_at')

    # Total Revenue (Only Paid)
    total_revenue = bills.filter(
        payment_status='Paid'
    ).aggregate(total=Sum('amount'))['total'] or 0
     
    context = {
        'bills': bills,
        'total_revenue': total_revenue,
        'action': 'billing',
        "role": "admin"
    }

    return render(request, 'dashboard/billing.html', context)


@login_required(login_url='/dash_login')
@staff_member_required
def billing_invoice(request, id):
    bill = get_object_or_404(Billing, id=id)

    return render(request, 'dashboard/billing_invoice.html', {
        'bill': bill
    })

@login_required(login_url='/dash_login')
@staff_member_required
def analytics(request):

    # Basic Stats
    total_doctors = Doctor.objects.count()
    total_patients = Patients.objects.count()
    total_appointments = Appointment.objects.count()

    # Dates
    today = timezone.now().date()
    week_start = today - timedelta(days=7)


    # Today Revenue
    today_revenue = Billing.objects.filter(
        payment_status='Paid',
        created_at__date=today
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Weekly Revenue (Last 7 days)
    weekly_revenue = Billing.objects.filter(
        payment_status='Paid',
        created_at__date__gte=week_start
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Monthly Revenue
    monthly_revenue = Billing.objects.filter(
        payment_status='Paid',
        created_at__year=today.year,
        created_at__month=today.month
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Total Revenue
    total_revenue = Billing.objects.filter(
        payment_status='Paid'
    ).aggregate(total=Sum('amount'))['total'] or 0


    appointments_chart = (
        Appointment.objects
        .annotate(day=ExtractWeekDay('appointment_date'))
        .values('day')
        .annotate(total=Count('id'))
        .order_by('day')
    )

    days_map = {
        1: 'Sun', 2: 'Mon', 3: 'Tue',
        4: 'Wed', 5: 'Thu', 6: 'Fri', 7: 'Sat'
    }

    chart_labels = []
    chart_data = []

    for item in appointments_chart:
        chart_labels.append(days_map[item['day']])
        chart_data.append(item['total'])


    completed_appointments = Appointment.objects.filter(status='Approved').count()
    pending_appointments = Appointment.objects.filter(status='Pending').count()
    cancelled_appointments = Appointment.objects.filter(status='Cancelled').count()


    top_doctors = (
        Appointment.objects
        .values('doctor__id', 'doctor__name')
        .annotate(total=Count('id'))
        .order_by('-total')[:5]
    )

    top_patients = (
        Appointment.objects
        .values('user__id', 'user__username')
        .annotate(total=Count('id'))
        .order_by('-total')[:5]
    )

    context = {
        'action': 'analytics',
        "role": "admin",

        # Stats
        "total_doctors": total_doctors,
        "total_patients": total_patients,
        "total_appointments": total_appointments,

        # Charts
        "chart_labels": chart_labels,
        "chart_data": chart_data,

        # Status
        "completed_appointments": completed_appointments,
        "pending_appointments": pending_appointments,
        "cancelled_appointments": cancelled_appointments,

        # Top Lists
        "top_doctors": top_doctors,
        "top_patients": top_patients,

        #  Revenue (FINAL)
        "today_revenue": today_revenue,
        "weekly_revenue": weekly_revenue,
        "monthly_revenue": monthly_revenue,
        "total_revenue": total_revenue,
    }

    return render(request, "dashboard/analytics.html", context)


@login_required(login_url='/dash_login')
@staff_member_required
def setting(request):
    user = request.user   # current logged-in admin

    if request.method == "POST":
        # Profile Update
        if "profile_update" in request.POST:
            user.first_name = request.POST.get('full_name')
            user.email = request.POST.get('email')

            user.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('settings')

        # Password Update
        if "password_update" in request.POST:
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            if not user.check_password(current_password):
                messages.error(request, "Current password is incorrect!")
            elif new_password != confirm_password:
                messages.error(request, "Passwords do not match!")
            else:
                user.set_password(new_password)
                user.save()
                messages.success(request, "Password updated successfully!")
                return redirect('dash_login')  

    context = {
        'user': user,
        'action': 'settings',
        'role': 'admin',
    }
    return render(request, "dashboard/settings.html", context)



def doctor_feedback(request):
    doctor_id = request.session.get('doctor_id')

    if not doctor_id:
        return redirect('dash_login')

    doctor = get_object_or_404(Doctor, id=doctor_id)

    comments_list = Comment.objects.filter(doctor=doctor)\
        .select_related('patient')\
        .order_by('-created_at')
        

    # pagination
    paginator = Paginator(comments_list, 5)
    page_number = request.GET.get('page')
    comments = paginator.get_page(page_number)

    context = {
        'comments': comments,
        'doctor': doctor,
        'action': 'feedback',
        'role': 'doctor',
    }

    return render(request, 'dashboard/doctor_feedback.html', context)

def approve_comment(request, comment_id):
    doctor_id = request.session.get('doctor_id')

    if not doctor_id:
        return redirect('dash_login')

    comment = get_object_or_404(Comment, id=comment_id)

    if comment.doctor.id == doctor_id:
        comment.is_approved = True
        comment.save()

    return redirect('doctor_feedback')


def delete_comment(request, comment_id):
    doctor_id = request.session.get('doctor_id')

    if not doctor_id:
        return redirect('dash_login')

    comment = get_object_or_404(Comment, id=comment_id)

    # security check
    if comment.doctor.id == doctor_id:
        comment.delete()

    return redirect('doctor_feedback')

