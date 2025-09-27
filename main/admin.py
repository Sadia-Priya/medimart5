from django.contrib import admin
from .models import (
    Category, Product, Order, OrderItem, Doctor,
    Schedule, Appointment, Prescription
)

# -----------------------
# Category Admin
# -----------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description')
    search_fields = ('name', 'description')
    list_filter = ('name',)


# -----------------------
# Product Admin
# -----------------------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'price')
    search_fields = ('name', 'description')
    list_filter = ('category',)


# -----------------------
# Order Admin
# -----------------------
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('price', 'quantity', 'product')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at', 'is_paid', 'total_price', 'payment_method')
    list_filter = ('is_paid', 'created_at', 'payment_method')
    search_fields = ('user__username', 'user__email')
    inlines = [OrderItemInline]


# -----------------------
# Doctor Admin
# -----------------------

class ScheduleInline(admin.TabularInline):
    model = Schedule
    extra = 0


class AppointmentInline(admin.TabularInline):
    model = Appointment
    extra = 0
    readonly_fields = ('date', 'time', 'patient', 'status')


class PrescriptionInline(admin.TabularInline):
    model = Prescription
    extra = 0
    readonly_fields = ('patient', 'uploaded_at', 'status')


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialty', 'location', 'fee', 'user', 'doctor_type')
    search_fields = ('name', 'specialty', 'languages', 'location', 'user__username')
    list_filter = ('specialty', 'location', 'doctor_type')
    inlines = [ScheduleInline, AppointmentInline, PrescriptionInline]



# -----------------------
# Appointment Admin
# -----------------------
@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'doctor', 'patient', 'date', 'time', 'visit_type', 'status')
    search_fields = ('doctor__name', 'patient__username')
    list_filter = ('status', 'visit_type', 'date')


# -----------------------
# Prescription Admin
# -----------------------
@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'doctor', 'status', 'uploaded_at')
    search_fields = ('patient__username', 'doctor__name')
    list_filter = ('status', 'uploaded_at')


# -----------------------
# Schedule Admin
# -----------------------
@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('id', 'doctor', 'day', 'start_time', 'end_time')
    search_fields = ('doctor__name', 'day')
    list_filter = ('day', 'doctor')


from django.contrib import admin
from .models import PetCategory, PetProduct

# Inline for products inside category
class PetProductInline(admin.TabularInline):
    model = PetProduct
    extra = 1  # how many empty product forms to show
    fields = ('name', 'price', 'prescription_required', 'image')
    show_change_link = True

# Category admin with products inline
@admin.register(PetCategory)
class PetCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    inlines = [PetProductInline]  # show products inside category page

# Product admin (still separate if needed)
@admin.register(PetProduct)
class PetProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "price", "prescription_required")
    list_filter = ("category", "prescription_required")
    search_fields = ("name",)


from django.contrib import admin
from .models import eLabSchedule


@admin.register(eLabSchedule)
class eLabScheduleAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'test_name', 'preferred_date', 'report_verified')
    list_filter = ('test_type', 'report_verified')
    search_fields = ('user__username', 'test_name')
    readonly_fields = ('user', 'test_type', 'test_name', 'test_price', 'preferred_date', 'preferred_time', 'address', 'phone')
