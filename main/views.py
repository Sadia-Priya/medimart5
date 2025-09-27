# main/views.py
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone

from django.views.decorators.csrf import csrf_protect
from django.db import transaction
from django.db.models import F, Sum

from .models import (
    Category, Product, Order, OrderItem,
    Prescription, Cart, Doctor, Schedule, Appointment, CartItem, PetProduct, eLabSchedule
)
from .forms import SignupForm, PrescriptionForm, AppointmentPrescriptionForm, eLabReportUploadForm


# -------------------- HOME & CATEGORIES --------------------

def index(request):
    categories = Category.objects.all()
    return render(request, 'main/index.html', {'categories': categories})


def category_list(request):
    categories = Category.objects.all()
    return render(request, 'main/category.html', {'categories': categories})


def product_list(request, category_id: int):
    category = get_object_or_404(Category, id=category_id)
    products = Product.objects.filter(category=category)
    return render(request, 'main/product_list.html', {'category': category, 'products': products})


def search(request):
    query = request.GET.get('q', '').strip()
    products = Product.objects.filter(name__icontains=query) if query else []
    return render(request, 'main/search.html', {'query': query, 'products': products})


# -------------------- AUTHENTICATION --------------------

@csrf_protect
def signup_view(request):
    if request.user.is_authenticated:
        messages.info(request, 'You are already logged in.')
        return redirect('index')

    if request.method == 'POST':
        form = SignupForm(request.POST)
        role = request.POST.get('role')  # 'patient' or 'doctor'

        if form.is_valid():
            user = form.save()

            if role == 'doctor':
                Doctor.objects.create(
                    user=user,
                    name=user.username,
                    specialty='',
                    languages='',
                    location='',
                    fee=0,
                    bio=''
                )

            messages.success(request, f'Account created successfully as {role}! You can now log in.')
            logout(request)
            return redirect('login')
    else:
        form = SignupForm()

    return render(request, 'main/signup.html', {'form': form})


@csrf_protect
def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if hasattr(user, 'doctor_profile'):
                return redirect('doctor_dashboard')
            else:
                return redirect('patient_dashboard')
    else:
        form = AuthenticationForm()

    return render(request, 'main/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('index')


# -------------------- CART & CHECKOUT --------------------

# imports
from django.db import transaction
from django.db.models import F, Sum

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Product, PetProduct, Cart, CartItem

@login_required
def add_to_cart(request, product_id):
    cart, _ = Cart.objects.get_or_create(user=request.user)

    # Try normal Product first
    try:
        product = Product.objects.get(id=product_id)
        item, created = CartItem.objects.get_or_create(
            cart=cart, product=product, pet_product=None, defaults={'quantity': 1}
        )
        if not created:
            item.quantity += 1
            item.save()
        messages.success(request, f"{product.name} added to cart.")
        return redirect('cart')

    except Product.DoesNotExist:
        pass

    # Try PetProduct
    try:
        pet_product = PetProduct.objects.get(id=product_id)
        item, created = CartItem.objects.get_or_create(
            cart=cart, product=None, pet_product=pet_product, defaults={'quantity': 1}
        )
        if not created:
            item.quantity += 1
            item.save()
        messages.success(request, f"{pet_product.name} added to cart.")
        return redirect('cart')

    except PetProduct.DoesNotExist:
        messages.error(request, "Product not found.")
        return redirect('cart')


@login_required
def update_cart(request, product_id: int):
    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', '1'))
        except ValueError:
            quantity = 1

        cart = Cart.objects.filter(user=request.user).first()
        if not cart:
            return redirect('cart')

        # Support both Product and PetProduct
        cart_item = CartItem.objects.filter(cart=cart, product_id=product_id).first()
        if not cart_item:
            cart_item = CartItem.objects.filter(cart=cart, pet_product_id=product_id).first()

        if cart_item:
            if quantity > 0:
                cart_item.quantity = quantity
                cart_item.save()
                item_name = cart_item.product.name if cart_item.product else cart_item.pet_product.name
                messages.success(request, f"Updated quantity for {item_name}.")
            else:
                cart_item.delete()
                messages.info(request, "Item removed from cart.")

    return redirect('cart')


@login_required
def remove_from_cart(request, product_id: int):
    cart = Cart.objects.filter(user=request.user).first()
    if cart:
        deleted_count = CartItem.objects.filter(cart=cart, product_id=product_id).delete()[0]
        if not deleted_count:
            CartItem.objects.filter(cart=cart, pet_product_id=product_id).delete()
    return redirect('cart')


from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import F, Sum
from .models import Cart, Prescription

from decimal import Decimal
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Cart, CartItem, Prescription

@login_required
def cart_view(request):
    cart = Cart.objects.filter(user=request.user).first()
    cart_items = cart.items.select_related('product', 'pet_product') if cart else []

    # Check prescription requirement
    presc_ids = {ci.product_id for ci in cart_items if ci.product and ci.product.requires_prescription} | \
                {ci.pet_product_id for ci in cart_items if ci.pet_product and ci.pet_product.prescription_required}

    prescription_required = bool(presc_ids)

    if prescription_required:
        approved_count = (Prescription.objects
                          .filter(patient=request.user, status='approved', products__in=presc_ids)
                          .values('products')
                          .distinct()
                          .count())
        has_approved_prescription = (approved_count == len(presc_ids))
    else:
        has_approved_prescription = True

    # Compute total
    total = cart.total_price() if cart else Decimal('0.00')

    context = {
        'cart_items': cart_items,
        'total': total,
        'prescription_required': prescription_required,
        'has_approved_prescription': has_approved_prescription,
    }
    return render(request, 'main/cart.html', context)


@login_required
def checkout(request):
    # Load cart
    cart = Cart.objects.filter(user=request.user).first()
    if not cart or not cart.items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect('cart')

    # Prefetch items
    cart_items = cart.items.select_related('product', 'pet_product')

    # Compute total using subtotal property
    total = sum(item.subtotal for item in cart_items)

    # RX gating: check for prescription-required products
    rx_product_ids = [ci.product_id for ci in cart_items if ci.product and ci.product.requires_prescription]
    needs_rx = bool(rx_product_ids)

    has_approved = True
    if needs_rx:
        approved_count = (
            Prescription.objects
            .filter(patient=request.user, status='approved', products__in=rx_product_ids)
            .values('products')
            .distinct()
            .count()
        )
        has_approved = (approved_count == len(rx_product_ids))

    if needs_rx and not has_approved:
        messages.warning(request, "Upload an approved prescription for prescription items before checkout.")
        return redirect('upload_prescription')

    payment_methods = ['Bkash', 'Nogod', 'Cash on Delivery']

    # Place order
    if request.method == 'POST':
        method = request.POST.get('payment_method')
        if not method:
            messages.error(request, "Please select a payment method.")
            return redirect('checkout')

        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                total_price=total,
                payment_method=method,
                status="pending",
                is_paid=(method != "Cash on Delivery"),
            )

            # Create order items, preserving name & price
            for it in cart_items:
                item_name, item_price = (
                    (it.product.name, it.product.price) if it.product
                    else (it.pet_product.name, it.pet_product.price) if it.pet_product
                    else ("Unknown Product", 0)
                )

                OrderItem.objects.create(
                    order=order,
                    product=it.product,
                    pet_product=it.pet_product,
                    quantity=it.quantity,
                    price=item_price,
                    name=item_name
                )

            # Clear cart
            cart.items.all().delete()

        messages.success(request, f"Your order #{order.id} has been placed successfully!")
        return redirect('patient_dashboard')

    # Render checkout page
    return render(request, 'main/checkout.html', {
        'cart_items': cart_items,
        'total': total,
        'payment_methods': payment_methods,
        'prescription_required': needs_rx,
        'has_approved_prescription': has_approved,
    })




# -------------------- DOCTORS & APPOINTMENTS --------------------

def doctor_list(request):
    doctors = Doctor.objects.all()
    return render(request, "main/doctors_list.html", {"doctors": doctors})


def doctor_profile(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    schedules = Schedule.objects.filter(doctor=doctor).order_by('day', 'start_time')
    today = timezone.now().date()
    is_doctor = request.user.groups.filter(name='Doctor').exists() if request.user.is_authenticated else False

    return render(request, "main/doctor_profile.html", {
        "doctor": doctor,
        "schedules": schedules,
        "today": today,
        "is_doctor": is_doctor,
    })


@login_required
def book_appointment(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)

    if request.method == "POST":
        visit_type = request.POST.get("visitType")
        date = request.POST.get("date")
        time = request.POST.get("time")
        notes = request.POST.get("notes", "")

        exists = Appointment.objects.filter(doctor=doctor, date=date, time=time).exists()
        if exists:
            messages.error(request, "This time slot is already booked. Please choose another.")
            return redirect("doctor_profile", doctor_id=doctor.id)

        Appointment.objects.create(
            doctor=doctor,
            patient=request.user,
            visit_type=visit_type,
            date=date,
            time=time,
            notes=notes,
        )
        messages.success(request, "Appointment booked successfully.")

        if request.user.groups.filter(name='Doctor').exists():
            return redirect('doctor_appointments')
        else:
            return redirect('patient_dashboard')

    return redirect("doctor_profile", doctor_id=doctor.id)


# -------------------- PRESCRIPTIONS --------------------

# views.py
from django.contrib.auth.decorators import login_required

@login_required
def upload_prescription(request):
    cart = Cart.objects.filter(user=request.user).first()
    cart_items = cart.items.select_related('product') if cart else []
    # Compute RX need from flags
    prescription_required = any(ci.product.requires_prescription for ci in cart_items) if cart_items else False  # [web:221]

    # If no RX needed, go back to cart (do not jump to checkout here)
    if not prescription_required:
        messages.info(request, "No prescription required for your cart items.")
        return redirect('cart')  # keep flow consistent; checkout will re-check anyway [web:221]

    if request.method == 'POST':
        form = PrescriptionForm(request.POST, request.FILES)
        if form.is_valid():
            p = Prescription.objects.create(
                patient=request.user, image=form.cleaned_data['image'], status='pending'
            )  # [web:221]
            # Link only RX items currently in cart
            for it in cart_items:
                if it.product.requires_prescription:
                    p.products.add(it.product)  # [web:221]
            messages.success(request, "Prescription uploaded successfully. Wait for approval.")
            return redirect('cart')  # return to cart; button will remain disabled until approved [web:221]
    else:
        form = PrescriptionForm()

    return render(request, 'main/upload_prescription.html', {
        'form': form,
        'prescription_required': prescription_required,
    })  # [web:267]



@login_required
def my_prescriptions(request):
    prescriptions = Prescription.objects.filter(patient=request.user)
    return render(request, 'main/my_prescriptions.html', {'prescriptions': prescriptions})


@login_required
def review_prescriptions(request):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to review prescriptions.")
        return redirect('index')

    prescriptions = Prescription.objects.filter(status='pending').order_by('uploaded_at')
    return render(request, 'main/review_prescriptions.html', {'prescriptions': prescriptions})


@login_required
def update_prescription_status(request, prescription_id):
    prescription = get_object_or_404(Prescription, id=prescription_id)
    if not hasattr(request.user, "doctor_profile"):
        messages.error(request, "You are not authorized to update prescriptions.")
        return redirect("requested_prescriptions")

    if request.method == "POST":
        status = request.POST.get("status")
        notes = request.POST.get("doctor_notes", "")
        prescription.status = status
        if status in ["approved", "rejected"]:
            prescription.doctor = request.user.doctor_profile
            prescription.doctor_notes = notes
        prescription.save()

        if status == "rejected":
            cart = Cart.objects.filter(user=prescription.patient).first()
            if cart:
                CartItem.objects.filter(
                    cart=cart,
                    product__in=prescription.products.all(),
                    product__requires_prescription=True
                ).delete()
        messages.success(request, f"Prescription {status.capitalize()} successfully.")
    return redirect("requested_prescriptions")


# -------------------- Doctor functions --------------------

@login_required
def doctor_dashboard(request):
    if not hasattr(request.user, 'doctor_profile'):
        messages.error(request, "You are not a doctor.")
        return redirect('index')

    doctor = request.user.doctor_profile
    appointments = Appointment.objects.filter(doctor=doctor).order_by('date', 'time')

    paid_appointments_count = appointments.filter(is_paid=True).count()
    total_earnings = sum(app.doctor.fee for app in appointments if app.is_paid)

    return render(request, 'main/doctor_dashboard.html', {
        'doctor': doctor,
        'appointments': appointments,
        'paid_appointments_count': paid_appointments_count,
        'total_earnings': total_earnings,
    })


@login_required
def requested_prescriptions(request):
    if not hasattr(request.user, 'doctor_profile'):
        messages.error(request, "You are not a doctor.")
        return redirect('index')

    prescriptions = Prescription.objects.filter(status='pending').order_by('-uploaded_at')
    context = {
        'prescriptions': prescriptions,
        'is_doctor': True,
    }
    return render(request, 'main/requested_prescriptions.html', context)


@login_required
def patient_dashboard(request):
    user = request.user  # <-- Add this line

    prescriptions = Prescription.objects.filter(patient=request.user).order_by('-uploaded_at')
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    appointments = Appointment.objects.filter(patient=request.user).order_by('date', 'time')
    elab_schedules = eLabSchedule.objects.filter(user=user)  # Add this line

    if not prescriptions.exists() and not appointments.exists() and not orders.exists():
        return redirect('index')

    context = {
        'prescriptions': prescriptions,
        'orders': orders,
        'appointments': appointments,
        'elab_schedules': elab_schedules,  # Pass to template

    }
    return render(request, 'main/patient_dashboard.html', context)


@staff_member_required
def manage_users(request):
    users = User.objects.all()
    return render(request, 'main/manage_users.html', {'users': users})


@login_required
def order_status(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'main/order_status.html', {'orders': orders})


@login_required
def upload_appointment_prescription(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, doctor__user=request.user)

    if request.method == "POST":
        form = AppointmentPrescriptionForm(request.POST, request.FILES, instance=appointment)
        if form.is_valid():
            form.save()
            messages.success(request, "Prescription uploaded successfully for this appointment.")
            return redirect("doctor_appointments")
    else:
        form = AppointmentPrescriptionForm(instance=appointment)

    return render(request, "main/upload_appointment_prescription.html", {
        "form": form,
        "appointment": appointment
    })


@login_required
def doctor_appointments(request):
    if not hasattr(request.user, 'doctor_profile'):
        messages.error(request, "You are not a doctor.")
        return redirect('index')

    doctor = request.user.doctor_profile
    appointments = (Appointment.objects
                    .filter(doctor=doctor)
                    .select_related('patient')  # small optimization [web:541]
                    .order_by('date', 'time'))

    for appointment in appointments:
        appointment.approved_prescription = Prescription.objects.filter(
            patient=appointment.patient, status='approved'
        ).first()  # avoid missing reverse accessor [web:221]

    return render(request, 'main/doctor_appointments.html', {
        'appointments': appointments,
        'doctor': doctor,
    })


@login_required
def pay_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)

    if request.method == "POST":
        transaction_id = request.POST.get("transaction_id")
        appointment.payment_method = "Bkash"
        appointment.transaction_id = transaction_id
        appointment.amount = appointment.doctor.fee
        appointment.is_paid = True
        appointment.save()

        messages.success(
            request,
            f"Payment of ৳{appointment.doctor.fee} received. Transaction ID: {transaction_id}."
        )
        return redirect('patient_dashboard')

    return render(request, 'main/pay_appointment.html', {'appointment': appointment})


from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib import messages

# --- Pet Care hub: show specific categories (Dog/Cat/Small Pets/Supplements) ---
from django.shortcuts import render
from .models import PetCategory

def pet_care(request):
    # fetch all pet categories
    categories = PetCategory.objects.all()
    return render(request, 'main/pet_care.html', {'categories': categories})


# --- Products for a Pet Category (Add to cart form will post to existing add_to_cart view) ---
def pet_category_products(request, category_id: int):
    category = get_object_or_404(PetCategory, id=category_id)  # ✅ Use PetCategory
    products = PetProduct.objects.filter(category=category)     # ✅ Use PetProduct
    return render(request, 'main/pet_category_products.html', {
        'category': category,
        'products': products
    })



# --- List only veterinarians ---
def pet_doctors(request):
    vets = Doctor.objects.filter(doctor_type='vet')
    return render(request, 'main/pet_doctors.html', {'vets': vets})

def pet_category_detail(request, category_id: int):
    category = get_object_or_404(PetCategory, id=category_id)
    products = PetProduct.objects.filter(category=category)
    return render(request, 'main/pet_category_detail.html', {
        'category': category,
        'products': products
    })



# --- Book an appointment with a veterinarian (GET shows form, POST creates appointment) ---
@login_required
def book_pet_appointment(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id, doctor_type='vet')

    if request.method == 'POST':
        date = request.POST.get('date')
        time = request.POST.get('time')
        pet_name = request.POST.get('pet_name', '').strip()
        notes = request.POST.get('notes', '').strip()

        # Validate slot availability (Appointment model already uses unique constraint on doctor+date+time)
        if Appointment.objects.filter(doctor=doctor, date=date, time=time).exists():
            messages.error(request, "This time slot is already booked. Please choose another.")
            return redirect('book_pet_appointment', doctor_id=doctor.id)

        # You can also add simple future-date validation
        if date:
            try:
                from datetime import datetime
                date_obj = datetime.strptime(date, "%Y-%m-%d").date()
                if date_obj < timezone.now().date():
                    messages.error(request, "Please select a valid future date.")
                    return redirect('book_pet_appointment', doctor_id=doctor.id)
            except ValueError:
                pass

        Appointment.objects.create(
            doctor=doctor,
            patient=request.user,
            visit_type='online',
            date=date, time=time,
            notes=(f"Pet: {pet_name}\n" + notes) if pet_name or notes else notes
        )

        messages.success(request, "Appointment booked successfully. The veterinarian will contact you.")
        return redirect('patient_dashboard')

    # GET
    return render(request, 'main/book_pet_appointment.html', {'doctor': doctor})

def pet_doctors(request):
    doctors = Doctor.objects.filter(doctor_type='vet')
    return render(request, 'main/pet_doctors.html', {'doctors': doctors})

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from .models import Doctor, Appointment

def book_vet_appointment(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id, doctor_type='vet')
    today = timezone.now().date()
    schedules = doctor.schedules.all() if hasattr(doctor, 'schedules') else []
    is_doctor = hasattr(request.user, 'doctor_profile')

    if request.method == "POST":
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        visit_type = request.POST.get('visitType')
        date = request.POST.get('date')
        time = request.POST.get('time')
        notes = request.POST.get('notes', '')

        Appointment.objects.create(
            doctor=doctor,
            patient=request.user if request.user.is_authenticated else None,
            patient_name=name,
            patient_phone=phone,
            visit_type=visit_type,
            date=date,
            time=time,
            notes=notes
        )
        messages.success(request, f"Appointment booked with {doctor.name} on {date} at {time}.")
        return redirect('book_vet_appointment', doctor_id=doctor.id)

    return render(request, 'main/vet_profile.html', {
        'doctor': doctor,
        'schedules': schedules,
        'is_doctor': is_doctor,
        'today': today,
    })


def add_pet_to_cart(request, petproduct_id):
    # your logic here

    pet = get_object_or_404(PetProduct, id=petproduct_id)
    cart, created = Cart.objects.get_or_create(user=request.user)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        pet_product=pet,
        defaults={'quantity': 1}
    )
    if not created:
        cart_item.quantity += 1
        cart_item.save()

    return redirect('cart')


# ---------------- Update PetProduct Quantity ----------------
@login_required
def update_pet_cart(request, petproduct_id):
    if request.method == "POST":
        cart, _ = Cart.objects.get_or_create(user=request.user)
        item = get_object_or_404(CartItem, cart=cart, pet_product_id=petproduct_id)
        try:
            quantity = int(request.POST.get("quantity", 1))
            if quantity > 0:
                item.quantity = quantity
                item.save()
                messages.success(request, f"{item.pet_product.name} quantity updated.")
            else:
                messages.error(request, "Quantity must be at least 1.")
        except ValueError:
            messages.error(request, "Invalid quantity.")
    return redirect("cart")

# ---------------- Remove PetProduct from Cart ----------------
@login_required
def remove_pet_from_cart(request, petproduct_id):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    item = get_object_or_404(CartItem, cart=cart, pet_product_id=petproduct_id)
    item.delete()
    messages.success(request, f"{item.pet_product.name} removed from cart.")
    return redirect("cart")


def contact(request):
    return render(request, 'main/contact.html')


from .forms import eLabScheduleForm

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import eLabScheduleForm
from .models import eLabSchedule

@login_required
def elab_schedule(request):
    if request.method == 'POST':
        form = eLabScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.user = request.user

            selected_name = form.cleaned_data['test_name']
            test_info = eLabScheduleForm.AVAILABLE_TESTS.get(selected_name)
            if test_info:
                schedule.test_type = test_info[0]
                schedule.test_price = test_info[1]

            schedule.is_paid = False
            schedule.payment_method = None
            schedule.transaction_id = None

            schedule.save()
            messages.success(request, 'Your test has been scheduled. Please complete the payment below.')
            return redirect('pay_elab', test_id=schedule.id)
    else:
        form = eLabScheduleForm()

    # Get the user's scheduled tests
    elab_schedules = eLabSchedule.objects.filter(user=request.user).order_by('-created_at')

    return render(request, 'main/elab.html', {
        'form': form,
        'elab_schedules': elab_schedules,
        'AVAILABLE_TESTS': eLabScheduleForm.AVAILABLE_TESTS,  # Pass this to the template!
    })


# views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import eLabSchedule
from .forms import eLabReportUploadForm
from django.contrib.auth.models import Group

@login_required
def doctor_elab_list(request):
    user = request.user

    # ✅ Check if user is a doctor (DoctorProfile OR Doctors group)
    is_doctor = hasattr(user, 'doctor_profile') or user.groups.filter(name='Doctors').exists()

    if not is_doctor:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('index')

    # Get all eLab tests
    elab_tests = eLabSchedule.objects.all()

    # Handle POST (uploading report)
    if request.method == 'POST':
        test_id = request.POST.get('test_id')
        try:
            test = eLabSchedule.objects.get(id=test_id)
        except eLabSchedule.DoesNotExist:
            messages.error(request, "Test not found.")
            return redirect('doctor_elab_list')

        form = eLabReportUploadForm(request.POST, request.FILES, instance=test)
        if form.is_valid():
            form.save()
            messages.success(request, f"Report for {test.test_name} updated successfully.")
            return redirect('doctor_elab_list')
        else:
            messages.error(request, "Failed to upload report. Check your inputs.")
    else:
        form = eLabReportUploadForm()  # empty form

    return render(request, 'main/doctor_elab_list.html', {
        'elab_tests': elab_tests,
        'form': form
    })

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import eLabSchedule  # adjust model name if different

@login_required
def pay_elab(request, test_id):
    test = get_object_or_404(eLabSchedule, id=test_id, user=request.user)

    if request.method == "POST":
        payment_method = request.POST.get("payment_method")
        transaction_id = request.POST.get("transaction_id", "").strip()

        if not payment_method or not transaction_id:
            messages.error(request, "Both payment method and Transaction ID are required.")
            return redirect("pay_elab", test_id=test.id)

        # Mark test as paid
        test.is_paid = True
        test.payment_method = payment_method
        test.transaction_id = transaction_id
        test.save()

        messages.success(request, f"✅ Payment recorded successfully for {test.test_name}.")
        return redirect("elab_schedule")  # Shows updated schedule list

    return render(request, "main/pay_elab.html", {"test": test})
