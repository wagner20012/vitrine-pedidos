from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from functools import wraps

from catalog.models import Category, Product
from core.models import AuditLog
from core.utils import money
from orders.models import Order, OrderItem, StockReservation


def staff_required(view):
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper


# ----------------------------------------------------------------- Dashboard


def _sales_total(qs):
    total = qs.filter(status__in=[Order.Status.PAID, Order.Status.PREPARING, Order.Status.READY, Order.Status.DELIVERED]).aggregate(t=Sum("total"))["t"]
    return money(total or 0)


@staff_required
def home(request):
    now = timezone.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    orders = Order.objects.all()
    context = {
        "orders_today": orders.filter(created_at__gte=today).count(),
        "orders_pending": orders.filter(
            status__in=[Order.Status.NEW, Order.Status.AWAITING_CONTACT, Order.Status.IN_ATTENDANCE]
        ).count(),
        "orders_awaiting_payment": orders.filter(status=Order.Status.AWAITING_PAYMENT).count(),
        "orders_paid": orders.filter(status=Order.Status.PAID).count(),
        "orders_cancelled": orders.filter(status=Order.Status.CANCELLED).count(),
        "sales_today": _sales_total(orders.filter(created_at__gte=today)),
        "sales_7d": _sales_total(orders.filter(created_at__gte=now - timedelta(days=7))),
        "sales_30d": _sales_total(orders.filter(created_at__gte=now - timedelta(days=30))),
        "stock_out": Product.objects.filter(is_active=True, stock__lte=0).count(),
        "stock_low": Product.objects.filter(is_active=True, stock__gt=0, stock__lte=F("min_stock")).count(),
        "backorder_count": Product.objects.filter(is_active=True, allow_backorder=True).count(),
        "products_total": Product.objects.count(),
        "products_active": Product.objects.filter(is_active=True).count(),
        "products_inactive": Product.objects.filter(is_active=False).count(),
        "products_promo": Product.objects.filter(is_active=True).exclude(discount_type=Product.DiscountType.NONE).count(),
        "recent_orders": orders[:8],
        "low_stock_products": Product.objects.filter(is_active=True).filter(
            Q(stock__lte=F("min_stock"))
        ).order_by("stock")[:8],
        "audit_entries": AuditLog.objects.all()[:8],
    }
    return render(request, "dashboard/home.html", context)


# ----------------------------------------------------------------- Pedidos


@staff_required
def order_list(request):
    status = request.GET.get("status", "").strip()
    search = request.GET.get("q", "").strip()
    orders = Order.objects.all()
    if status:
        orders = orders.filter(status=status)
    if search:
        from django.db.models import Q as _Q

        orders = orders.filter(_Q(number__icontains=search) | _Q(customer_name__icontains=search) | _Q(customer_phone__icontains=search))
    return render(
        request,
        "dashboard/order_list.html",
        {"orders": orders[:200], "status": status, "search": search, "statuses": Order.Status.choices},
    )


@staff_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    allowed = [
        s for s in Order.TRANSITIONS.get(Order.Status(order.status), set())
    ]
    status_labels = dict(Order.Status.choices)

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "change_status":
                new_status = request.POST.get("new_status")
                order.transition_to(new_status, user=request.user)
                from django.contrib import messages

                messages.success(request, f"Status atualizado para {status_labels.get(new_status, new_status)}.")
            elif action == "cancel":
                reason = request.POST.get("reason", "").strip() or "Cancelado pela administração."
                from orders.services import cancel_order

                cancel_order(order, user=request.user, reason=reason)
                from django.contrib import messages

                messages.success(request, "Pedido cancelado e estoque devolvido.")
        except ValueError as error:
            from django.contrib import messages

            messages.error(request, str(error))
        return redirect("dashboard:order_detail", order_id=order.pk)

    return render(
        request,
        "dashboard/order_detail.html",
        {"order": order, "allowed_transitions": allowed, "status_labels": status_labels},
    )


# ----------------------------------------------------------------- Produtos / estoque


@staff_required
def product_list(request):
    search = request.GET.get("q", "").strip()
    filter_by = request.GET.get("filtro", "").strip()
    products = Product.objects.select_related("category")
    if search:
        products = products.filter(Q(name__icontains=search) | Q(category__name__icontains=search))
    if filter_by == "sem_estoque":
        products = products.filter(stock__lte=0)
    elif filter_by == "estoque_baixo":
        products = products.filter(stock__gt=0, stock__lte=F("min_stock"))
    elif filter_by == "encomenda":
        products = products.filter(allow_backorder=True)
    elif filter_by == "promocao":
        products = products.exclude(discount_type=Product.DiscountType.NONE)
    elif filter_by == "inativos":
        products = products.filter(is_active=False)
    return render(request, "dashboard/product_list.html", {"products": products[:300], "search": search, "filter_by": filter_by})


# ----------------------------------------------------------------- Desconto em massa


@staff_required
def mass_discount(request):
    step = request.POST.get("step", "form")
    context = {}

    if request.method == "POST" and step == "preview":
        queryset = _mass_discount_queryset(request)
        action = request.POST.get("action_type", "percent")
        try:
            value = Decimal(request.POST.get("value", "0").replace(",", "."))
        except Exception:
            value = Decimal("0")
        context = {
            "step": "preview",
            "product_count": queryset.count(),
            "product_ids": ",".join(str(pk) for pk in queryset.values_list("pk", flat=True)),
            "action_type": action,
            "value": request.POST.get("value", "0"),
            "category": request.POST.get("category", ""),
            "only_promo": request.POST.get("only_promo", ""),
            "only_featured": request.POST.get("only_featured", ""),
            "only_inactive": request.POST.get("only_inactive", ""),
        }
        return render(request, "dashboard/mass_discount.html", {**context, "categories": Category.objects.all()})

    if request.method == "POST" and step == "execute":
        product_ids = [int(pk) for pk in request.POST.get("product_ids", "").split(",") if pk]
        action = request.POST.get("action_type", "percent")
        try:
            value = Decimal(request.POST.get("value", "0").replace(",", "."))
        except Exception:
            value = Decimal("0")
        products = Product.objects.filter(pk__in=product_ids)
        count = 0
        for product in products:
            old = f"{product.get_discount_type_display()} {product.discount_value}"
            if action == "remove":
                product.discount_type = Product.DiscountType.NONE
                product.discount_value = Decimal("0")
            elif action == "percent" and 0 < value <= 100:
                product.discount_type = Product.DiscountType.PERCENT
                product.discount_value = value
            elif action == "fixed" and value > 0:
                product.discount_type = Product.DiscountType.FIXED
                product.discount_value = min(value, product.price)
            else:
                continue
            product.save(update_fields=["discount_type", "discount_value", "updated_at"])
            count += 1
        AuditLog.log(
            "Desconto em massa aplicado",
            user=request.user,
            details=f"{count} produto(s) | ação: {action} | valor: {value}",
        )
        from django.contrib import messages

        messages.success(request, f"Desconto aplicado a {count} produto(s).")
        return redirect("dashboard:mass_discount")

    return render(request, "dashboard/mass_discount.html", {"step": "form", "categories": Category.objects.all()})


def _mass_discount_queryset(request):
    qs = Product.objects.all()
    category_id = request.POST.get("category")
    if category_id:
        qs = qs.filter(category_id=category_id)
    if request.POST.get("only_promo"):
        qs = qs.exclude(discount_type=Product.DiscountType.NONE)
    if request.POST.get("only_featured"):
        qs = qs.filter(is_featured=True)
    if request.POST.get("only_inactive"):
        qs = qs.filter(is_active=False)
    return qs


# ----------------------------------------------------------------- Relatórios


def _parse_period(request):
    preset = request.GET.get("periodo", "30")
    start = request.GET.get("inicio", "")
    end = request.GET.get("fim", "")
    now = timezone.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if preset == "hoje":
        return today, now
    if preset == "7":
        return today - timedelta(days=7), now
    if preset == "30":
        return today - timedelta(days=30), now
    if preset == "mes":
        return today.replace(day=1), now
    if preset == "custom" and start and end:
        from django.utils.dateparse import parse_date

        start_date = parse_date(start)
        end_date = parse_date(end)
        if start_date and end_date:
            return (
                timezone.make_aware(start_date.replace(hour=0, minute=0)),
                timezone.make_aware(end_date.replace(hour=23, minute=59, second=59)),
            )
    return today - timedelta(days=30), now


@staff_required
def reports(request):
    start, end = _parse_period(request)
    orders = Order.objects.filter(created_at__range=(start, end)).exclude(status=Order.Status.CANCELLED)

    paid_statuses = [Order.Status.PAID, Order.Status.PREPARING, Order.Status.READY, Order.Status.DELIVERED]
    sales_by_day = (
        orders.filter(status__in=paid_statuses)
        .values("created_at__date")
        .annotate(total=Sum("total"), count=Count("pk"))
        .order_by("created_at__date")
    )
    max_day = max((row["total"] for row in sales_by_day), default=0) or 1

    top_products = (
        OrderItem.objects.filter(order__in=orders)
        .values("product_name")
        .annotate(quantity=Sum("quantity"), revenue=Sum("subtotal"))
        .order_by("-quantity")[:10]
    )
    top_categories = (
        OrderItem.objects.filter(order__in=orders)
        .values("product__category__name")
        .annotate(quantity=Sum("quantity"), revenue=Sum("subtotal"))
        .order_by("-quantity")[:10]
    )

    return render(
        request,
        "dashboard/reports.html",
        {
            "start": start,
            "end": end,
            "sales_by_day": sales_by_day,
            "max_day": max_day,
            "top_products": top_products,
            "top_categories": top_categories,
            "orders_count": orders.count(),
            "revenue_total": money(orders.filter(status__in=paid_statuses).aggregate(t=Sum("total"))["t"] or 0),
        },
    )
