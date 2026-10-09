from uuid import uuid4

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from cart.services import load_cart
from core.models import StoreConfiguration
from orders.services import CartLineData, OrderError, create_order, release_expired_reservations, reserve_for_session

from .forms import CheckoutForm
from .models import Order
from .whatsapp import build_whatsapp_url


def _ensure_session(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def checkout(request):
    session_key = _ensure_session(request)
    cart = load_cart(request)
    if cart.is_empty:
        messages.info(request, "Seu carrinho está vazio.")
        return redirect("cart:detail")

    try:
        reserve_for_session(
            session_key,
            [CartLineData(product_id=line.product.pk, quantity=line.quantity) for line in cart.lines],
        )
    except OrderError as error:
        messages.error(request, str(error))
        return redirect("cart:detail")

    reservation_minutes = StoreConfiguration.load().reservation_minutes

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                order = create_order(
                    lines=[CartLineData(product_id=line.product.pk, quantity=line.quantity) for line in cart.lines],
                    customer_name=form.cleaned_data["customer_name"],
                    customer_phone=form.cleaned_data["customer_phone"],
                    note=form.cleaned_data["note"],
                    payment_method=form.cleaned_data["payment_method"],
                    idempotency_key=form.cleaned_data["idempotency_key"],
                    session_key=session_key,
                )
            except OrderError as error:
                messages.error(request, str(error))
                return redirect("cart:detail")
            except Exception:
                import logging

                logging.getLogger("orders").exception("Falha inesperada ao criar pedido")
                messages.error(request, "Não foi possível concluir esta operação. Tente novamente.")
                return redirect("cart:detail")

            # Pedido salvo e estoque tratado: agora sim limpar carrinho e liberar WhatsApp.
            from cart.services import clear_cart

            clear_cart(request)
            request.session["last_order_id"] = order.pk
            return redirect("orders:confirmation")

        # Se chegou aqui, o formulário tem erros de validação.
        return render(
            request,
            "orders/checkout.html",
            {"form": form, "cart": cart, "reservation_minutes": reservation_minutes},
            status=400,
        )

    form = CheckoutForm(initial={"idempotency_key": uuid4().hex})
    return render(
        request,
        "orders/checkout.html",
        {"form": form, "cart": cart, "reservation_minutes": reservation_minutes},
    )


def confirmation(request):
    order_id = request.session.get("last_order_id")
    if not order_id:
        return redirect("catalog:home")
    order = get_object_or_404(Order, pk=order_id)
    config = StoreConfiguration.load()
    whatsapp_url = build_whatsapp_url(order, config)
    return render(
        request,
        "orders/confirmation.html",
        {"order": order, "whatsapp_url": whatsapp_url, "store": config},
    )


@require_POST
def whatsapp_retry(request, order_id):
    """Reabrir o WhatsApp depois de uma falha: o pedido já está salvo no banco."""
    order = get_object_or_404(Order, pk=order_id)
    if request.session.get("last_order_id") != order.pk and not request.user.is_staff:
        messages.error(request, "Você não tem acesso a este pedido.")
        return redirect("catalog:home")
    config = StoreConfiguration.load()
    whatsapp_url = build_whatsapp_url(order, config)
    if not whatsapp_url:
        messages.error(request, "O WhatsApp não está configurado. Entre em contato com a loja.")
        return redirect("orders:confirmation")
    return redirect(whatsapp_url)
