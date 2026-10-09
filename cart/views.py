from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalog.models import Product

from .services import (
    add_to_cart,
    clear_cart,
    load_cart,
    remove_from_cart,
    update_quantity,
)
from orders.services import OrderError


def cart_detail(request):
    cart = load_cart(request)
    return render(request, "cart/cart.html", {"cart": cart})


@require_POST
def cart_add(request, product_id):
    quantity = request.POST.get("quantity", "1")
    try:
        quantity = max(1, int(quantity))
    except ValueError:
        quantity = 1
    try:
        add_to_cart(request, product_id, quantity)
        product = Product.objects.filter(pk=product_id).first()
        return redirect("cart:detail")
    except OrderError as error:
        from django.contrib import messages

        messages.error(request, str(error))
        return redirect(request.META.get("HTTP_REFERER") or "catalog:home")


@require_POST
def cart_update(request, product_id):
    quantity = request.POST.get("quantity", "1")
    try:
        quantity = int(quantity)
    except ValueError:
        quantity = 1
    try:
        update_quantity(request, product_id, quantity)
    except OrderError as error:
        from django.contrib import messages

        messages.error(request, str(error))
    return redirect("cart:detail")


@require_POST
def cart_remove(request, product_id):
    remove_from_cart(request, product_id)
    return redirect("cart:detail")


@require_POST
def cart_clear(request):
    clear_cart(request)
    return redirect("cart:detail")
