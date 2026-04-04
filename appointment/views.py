from django.shortcuts import render, redirect, get_object_or_404
from .models import Doctor, Category, Appointment, Patients, Contact, Billing
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.core.paginator import Paginator
import stripe
from django.conf import settings
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
    
    return render(request, 'doctor_info.html', {'doctor': doctor, 'releted_doctor': releted_doctor})

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
    


def book_appointment(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)

    if 'login' in request.session:
        email = request.session['login']  
        user = Patients.objects.get(email=email)
        
        
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
            
    else:
        messages.error(request, "Please Login Requered!")
        return redirect('login')
        
    return render(request, 'doctor_info.html', {'doctor': doctor,})

  
    
def approved_appointment(request, id):
    if 'login' in request.session:
        try:
            email = request.session['login']
            user = Patients.objects.get(email=email)

            appointment = get_object_or_404(Appointment, id=id, user=user)

            # ✅ Already approved check
            if appointment.status == 'Approved':
                messages.info(request, "Already Approved!")
                return redirect(request.META.get('HTTP_REFERER'))

            # ✅ Update status
            appointment.status = 'Approved'

            # ✅ Billing create (safe)
            if not appointment.is_billed:
                Billing.objects.create(
                    appointment=appointment,
                    amount=appointment.doctor.fees,
                    payment_status="Paid"
                )
                appointment.is_billed = True

            appointment.save()

            messages.success(request, "Appointment Completed & Billing Generated ✅")

        except Patients.DoesNotExist:
            messages.error(request, "User not found ❌")

    else:
        messages.error(request, "Please login required!")

    return redirect(request.META.get('HTTP_REFERER'))


def cancel_appointment(request, id):
    if 'login' in request.session:
        email = request.session['login']
        user = Patients.objects.get(email=email)

        appointment = get_object_or_404(Appointment, id=id, user=user)
        appointment.status = 'Cancelled'
        appointment.save()

        messages.success(request, "Appointment Cancelled Successfully!")
        return redirect(request.META.get('HTTP_REFERER'))
    else:
        messages.error(request, "Please login required!")
        return redirect('login')
    

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

    # ✅ Payment successful hone par update
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
            # 👉 delete old image from cloudinary
            if patient.profile_image:
                try:
                    cloudinary.uploader.destroy(patient.profile_image.public_id)
                except:
                    pass

            # 👉 assign new image
            patient.profile_image = new_image


        patient.save()
        messages.success(request, "Profile Updated succfully")

        return redirect('my_profile')  # ya jaha redirect karna hai

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

        return render(request, 'dashboard/index.html', {
            'action': 'admin',
            "role": "admin",

            # Stats
            'total_doctors': total_doctors,
            'appointment_total': appointment_total,
            'total_patients': total_patients,

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

    
    return render(request, 'dashboard/appointments.html', {'action': 'doctor_appointments',"role" : "doctor", 'appointments': appointments, "doctor": doctor})


@login_required(login_url=('/dash_login'))
@staff_member_required
def appointments(request):
    appointments_list = Appointment.objects.all().order_by('-created_at')
    
    total_appointments = appointments_list.count()
    completed_appointments = appointments_list.filter(status='Approved').count()
    pending_appointments = appointments_list.filter(status='Pending').count()
    cancelled_appointments = appointments_list.filter(status='Cancelled').count()

    paginator = Paginator(appointments_list, 10)  # 1 page = 10 records
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'dashboard/appointments.html', {
        'appointments': page_obj,
        'page_obj': page_obj,
        
        'total_appointments': total_appointments,
        'completed_appointments': completed_appointments,
        'pending_appointments': pending_appointments,
        'cancelled_appointments': cancelled_appointments,
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


@login_required(login_url=('/dash_login'))
@staff_member_required
def doctor_list(request):
    doctors = Doctor.objects.all().order_by('-id')
    
    total_doctor = doctors.count()
    available_doctor = doctors.filter(available=True).count()
    unavailable_doctor = doctors.filter(available=False).count()

    paginator = Paginator(doctors, 8)  # 1 page me 8 doctors
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'dashboard/doctor_list.html', {
        'doctors': page_obj,   # ⚠️ IMPORTANT
        'page_obj': page_obj,
        'total_doctor': total_doctor,
        'available_doctor': available_doctor,
        'unavailable_doctor': unavailable_doctor,
        'action': 'doctor_list',
        "role": "admin"
    })


@login_required(login_url=('/dash_login'))
@staff_member_required
def doctor_view(request, id):
    doctor = get_object_or_404(Doctor, id=id)

    return render(request, 'dashboard/doctor_view.html', {
        'doctor': doctor,
        'action': 'doctor_view',
        'role': 'admin'
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
        'action': 'patient_detail',
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
    month_start = today.replace(day=1)

    # Revenue Calculation (Doctor fees se)
    today_revenue = (
        Appointment.objects
        .filter(appointment_date=today, status='Approved')
        .aggregate(total=Sum(F('doctor__fees')))['total'] or 0
    )

    weekly_revenue = (
        Appointment.objects
        .filter(appointment_date__gte=week_start, status='Approved')
        .aggregate(total=Sum(F('doctor__fees')))['total'] or 0
    )

    monthly_revenue = (
        Appointment.objects
        .filter(appointment_date__gte=month_start, status='Approved')
        .aggregate(total=Sum(F('doctor__fees')))['total'] or 0
    )

    # Total Revenue
    total_revenue = (
        Appointment.objects
        .filter(status='Approved')
        .aggregate(total=Sum(F('doctor__fees')))['total'] or 0
    )
    
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

    # Status Chart
    completed_appointments = Appointment.objects.filter(status='Approved').count()
    pending_appointments = Appointment.objects.filter(status='Pending').count()
    cancelled_appointments = Appointment.objects.filter(status='Cancelled').count()
    
    # Top Doctors
    top_doctors = (
        Appointment.objects
        .values('doctor__id', 'doctor__name')
        .annotate(total=Count('id'))
        .order_by('-total')[:5]
    )

    # Top Patients
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

        "completed_appointments": completed_appointments,
        "pending_appointments": pending_appointments,
        "cancelled_appointments": cancelled_appointments,
        
        # Top Lists
        "top_doctors": top_doctors,
        "top_patients": top_patients,
        
        # 💰 Revenue
        "today_revenue": today_revenue,
        "weekly_revenue": weekly_revenue,
        "monthly_revenue": monthly_revenue,
        "total_revenue": total_revenue,
    }

    return render(request, "dashboard/analytics.html", context)


