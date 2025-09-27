from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.db.models import UniqueConstraint, CheckConstraint, Q, F, Sum
import uuid

# -------------------- CATEGORY & PRODUCT --------------------

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name='products', db_index=True
    )
    name = models.CharField(max_length=200, unique=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    description = models.TextField(blank=True)
    stock = models.PositiveIntegerField(default=0)
    requires_prescription = models.BooleanField(default=False, db_index=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)

    class Meta:
        constraints = [
            CheckConstraint(check=Q(stock__gte=0), name='product_stock_non_negative'),
        ]

    def __str__(self):
        return self.name


# -------------------- ORDER & ORDER ITEM --------------------

class Order(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('Bkash', 'Bkash'),
        ('Nogod', 'Nogod'),
        ('Cash on Delivery', 'Cash on Delivery'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_paid = models.BooleanField(default=False)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, default='Bkash')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Order {self.pk} by {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    # Preserve order history if a product is later removed from the catalog
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))

    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        pname = self.product.name if self.product else "Deleted product"
        return f"{pname} x {self.quantity}"


# -------------------- DOCTOR & SCHEDULE --------------------

from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User

DAYS_OF_WEEK = [
    ('Monday', 'Monday'),
    ('Tuesday', 'Tuesday'),
    ('Wednesday', 'Wednesday'),
    ('Thursday', 'Thursday'),
    ('Friday', 'Friday'),
    ('Saturday', 'Saturday'),
    ('Sunday', 'Sunday'),
]

class Doctor(models.Model):
    DOCTOR_TYPES = [
        ('human', 'Human Doctor'),
        ('vet', 'Veterinarian'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='doctor_profile',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100)
    specialty = models.CharField(max_length=100)
    doctor_type = models.CharField(
        max_length=10,
        choices=DOCTOR_TYPES,
        default='human'
    )
    languages = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    fee = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal('0.00')
    )
    bkash_number = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    bio = models.TextField(blank=True, null=True)   # ✅ fixed: allow empty bios
    image = models.ImageField(
        upload_to='doctor_images/',
        blank=True,
        null=True
    )

    def language_list(self):
        return [lang.strip() for lang in self.languages.split(',')]

    def __str__(self):
        return f"{self.name} ({self.get_doctor_type_display()})"


class Schedule(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='schedules')
    day = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        constraints = [
            UniqueConstraint(fields=('doctor', 'day', 'start_time', 'end_time'), name='uniq_schedule_slot'),
            CheckConstraint(check=Q(end_time__gt=F('start_time')), name='sched_time_order'),
        ]

    def __str__(self):
        return f"{self.doctor.name} - {self.day}: {self.start_time}-{self.end_time}"


# -------------------- APPOINTMENT --------------------

import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.db.models import UniqueConstraint


class Appointment(models.Model):
    VISIT_TYPE_CHOICES = [
        ('online', 'Online'),
        ('in-person', 'In-person'),
    ]

    # Optional: link to registered patient
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="appointments", null=True, blank=True)

    # For guest patients
    patient_name = models.CharField(max_length=100, blank=True, null=True)
    patient_phone = models.CharField(max_length=20, blank=True, null=True)

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="appointments")
    visit_type = models.CharField(max_length=20, choices=VISIT_TYPE_CHOICES)
    date = models.DateField()
    time = models.TimeField()
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='Booked')

    meeting_link = models.URLField(blank=True, null=True)
    prescription_file = models.FileField(upload_to='appointment_prescriptions/', blank=True, null=True)

    # Payment fields
    is_paid = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    transaction_id = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=('doctor', 'date', 'time'), name='uniq_doctor_slot'),
        ]
        ordering = ['date', 'time']

    def save(self, *args, **kwargs):
        # Auto-assign online meeting link if needed
        if self.visit_type == "online" and not self.meeting_link:
            unique_id = uuid.uuid4().hex[:8]
            self.meeting_link = f"https://meet.jit.si/medimart-{unique_id}"

        # Auto-set amount based on doctor fee if not set
        if (self.amount is None or self.amount == 0) and self.doctor:
            self.amount = self.doctor.fee

        # If patient is logged in, auto-fill patient_name and phone (optional)
        if self.patient and (not self.patient_name or not self.patient_phone):
            self.patient_name = self.patient.get_full_name() or self.patient.username
            # Assuming you store phone in User.profile.phone or similar
            profile = getattr(self.patient, 'profile', None)
            if profile and hasattr(profile, 'phone'):
                self.patient_phone = profile.phone

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Appointment with {self.doctor.name} on {self.date} at {self.time}"


# -------------------- PRESCRIPTION --------------------

class Prescription(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    patient = models.ForeignKey(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='prescriptions/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True, related_name='checked_prescriptions')
    doctor_notes = models.TextField(blank=True, null=True)
    # Link only to the items that need a prescription
    products = models.ManyToManyField('Product', blank=True, related_name='prescriptions')

    def __str__(self):
        return f"{self.patient.username} - {self.status}"


from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum, F, Q

from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum, F

# -------------------- CATEGORY & PET PRODUCT --------------------
class PetCategory(models.Model):
    name = models.CharField(max_length=255)
    short_desc = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='pet_categories/', blank=True, null=True)

    def __str__(self):
        return self.name

class PetProduct(models.Model):
    category = models.ForeignKey(PetCategory, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    prescription_required = models.BooleanField(default=False)
    image = models.ImageField(upload_to='pet_products/', blank=True, null=True)

    def __str__(self):
        return self.name

# -------------------- CART & CART ITEM --------------------
class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def total_price(self):
        agg_product = self.items.filter(product__isnull=False).aggregate(
            total=Sum(F('quantity') * F('product__price'))
        )['total'] or Decimal('0.00')
        agg_pet = self.items.filter(pet_product__isnull=False).aggregate(
            total=Sum(F('quantity') * F('pet_product__price'))
        )['total'] or Decimal('0.00')
        return agg_product + agg_pet

    def has_prescription_medicine(self):
        return self.items.filter(
            models.Q(product__requires_prescription=True) |
            models.Q(pet_product__prescription_required=True)
        ).exists()

    def __str__(self):
        return f"Cart of {self.user.username}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', null=True, blank=True, on_delete=models.CASCADE)
    pet_product = models.ForeignKey('PetProduct', null=True, blank=True, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def subtotal(self):
        if self.product:
            return self.quantity * self.product.price
        elif self.pet_product:
            return self.quantity * self.pet_product.price
        return Decimal('0.00')

    def __str__(self):
        name = self.product.name if self.product else (self.pet_product.name if self.pet_product else "Unknown Product")
        return f"{name} x {self.quantity}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    pet_product = models.ForeignKey('PetProduct', on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    name = models.CharField(max_length=255, blank=True, null=False)  # store name at order time

    def save(self, *args, **kwargs):
        if not self.name:
            if self.product:
                self.name = self.product.name
            elif self.pet_product:
                self.name = self.pet_product.name
            else:
                self.name = "Unknown Product"
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.name} x {self.quantity}"


from django.db import models
from django.contrib.auth.models import User

class eLabSchedule(models.Model):
    TEST_TYPE_CHOICES = [
        ('Blood', 'Blood'),
        ('Urine', 'Urine'),
        ('Pathology', 'Pathology'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('bkash', 'bKash'),
        ('nagad', 'Nagad'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    test_type = models.CharField(max_length=100, choices=TEST_TYPE_CHOICES)
    test_name = models.CharField(max_length=100)
    test_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    preferred_date = models.DateField()
    preferred_time = models.TimeField()
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    # Report
    report_file = models.FileField(upload_to='elab_reports/', null=True, blank=True)
    report_verified = models.BooleanField(default=False)

    # Payment
    is_paid = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.test_name} ({self.test_type}) for {self.user.username} on {self.preferred_date}"
