from core.models import StoreConfiguration
from catalog.models import Category


def store_settings(request):
    cart = request.session.get("beauty_cart", {})
    count = 0
    for value in cart.values():
        try:
            count += int(value)
        except (TypeError, ValueError):
            pass
    return {
        "store": StoreConfiguration.load(),
        "cart_count": count,
        "header_categories": Category.objects.filter(is_active=True)[:8],
    }
