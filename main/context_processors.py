# main/context_processors.py

from .models import Cart

def cart_count(request):
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        count = cart.items.count() if cart and hasattr(cart, 'items') else 0
    else:
        cart_session = request.session.get('cart', {})
        count = sum(cart_session.values()) if isinstance(cart_session, dict) else 0
    return {'cart_count': count}


def user_group_flags(request):
    """
    Returns flags for user roles:
    - is_doctor: True if user has a Doctor profile or is in 'Doctors' group
    - is_patient: True if user is authenticated but not a doctor
    - is_staff: True if user.is_staff
    """
    user = getattr(request, 'user', None)
    is_doctor = False
    is_patient = False
    is_staff = False

    if user and user.is_authenticated:
        is_staff = user.is_staff

        # Check doctor by profile or group
        try:
            is_doctor = hasattr(user, 'doctor_profile') or user.groups.filter(name='Doctors').exists()
        except:
            is_doctor = False

        is_patient = not is_doctor

    return {
        'is_doctor': is_doctor,
        'is_patient': is_patient,
        'is_staff': is_staff,
    }
