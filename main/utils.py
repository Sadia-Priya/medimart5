
from .models import Cart

def get_user_cart(user):
    # Get the latest cart for this user or create a new one
    cart, created = Cart.objects.get_or_create(user=user)
    return cart
