"""
URL definitions for the main application. These routes map URL
patterns to corresponding view functions defined in views.py.
"""

from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from main.views import doctor_elab_list

urlpatterns = [
    # ---------------- Home & Categories ----------------
    path('', views.index, name='index'),
    path('categories/', views.category_list, name='category_list'),
    path('category/<int:category_id>/', views.product_list, name='product_list'),
    path('search/', views.search, name='search'),

    # ---------------- Authentication ----------------
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ---------------- Cart & Checkout ----------------
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:product_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),

    # ---------------- Doctors & Appointments ----------------
    path('doctors/', views.doctor_list, name='doctors_list'),
    path('doctor/<int:doctor_id>/', views.doctor_profile, name='doctor_profile'),
    path('doctor/<int:doctor_id>/book/', views.book_appointment, name='book_appointment'),
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor/appointments/', views.doctor_appointments, name='doctor_appointments'),
    path('doctor/appointments/upload/<int:appointment_id>/', views.upload_appointment_prescription, name='upload_appointment_prescription'),

    # ---------------- Prescriptions ----------------
    path('upload-prescription/', views.upload_prescription, name='upload_prescription'),
    path('my-prescriptions/', views.my_prescriptions, name='my_prescriptions'),
    path('review-prescriptions/', views.review_prescriptions, name='review_prescriptions'),
    path('update-prescription/<int:prescription_id>/', views.update_prescription_status, name='update_prescription_status'),
    path('requested-prescriptions/', views.requested_prescriptions, name='requested_prescriptions'),

    # ---------------- Patient ----------------
    path('patient/dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('patient/orders/', views.order_status, name='order_status'),
    path('appointment/pay/<int:appointment_id>/', views.pay_appointment, name='pay_appointment'),

    # ---------------- Admin / Staff ----------------
    path('manage-users/', views.manage_users, name='manage_users'),

    # ---------------- Pet Care ----------------
    path('pet-care/', views.pet_care, name='pet_care'),
    path('pet-care/category/<int:category_id>/products/', views.pet_category_products, name='pet_category_products'),
    path('pet-care/category/<int:category_id>/detail/', views.pet_category_detail, name='pet_category_detail'),

    path('pet-care/doctors/', views.pet_doctors, name='pet_doctors'),
    path('pet-care/book/<int:doctor_id>/', views.book_pet_appointment, name='book_pet_appointment'),
    path('pet-care/doctors/book/<int:doctor_id>/', views.book_vet_appointment, name='book_vet_appointment'),

    # Pet Cart
    path('cart/add/pet/<int:petproduct_id>/', views.add_pet_to_cart, name='add_pet_to_cart'),
    path('cart/update/pet/<int:petproduct_id>/', views.update_pet_cart, name='update_pet_cart'),
    path('cart/remove/pet/<int:petproduct_id>/', views.remove_pet_from_cart, name='remove_pet_from_cart'),

    # ---------------- Misc ----------------
    path('contact/', views.contact, name='contact'),
    path('elab/', views.elab_schedule, name='elab_schedule'),
    path('doctor/elab/', doctor_elab_list, name='doctor_elab_list'),
    path("elab/pay/<int:test_id>/", views.pay_elab, name="pay_elab"),

]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
