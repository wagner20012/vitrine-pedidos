from decimal import Decimal, InvalidOperation

from django.db.models import Case, DecimalField, F, Q, Value, When
from django.db.models.functions import Least
from django.shortcuts import render
from django.views.generic import DetailView, ListView

from cart.services import get_reserved_map
from core.models import Banner
from orders.models import OrderItem

from .models import Category, Product, ProductImage

PRODUCTS_PER_PAGE = 12

SORT_OPTIONS = (
    ("relevancia", "Mais relevantes"),
    ("menor_preco", "Menor preço"),
    ("maior_preco", "Maior preço"),
    ("recentes", "Mais recentes"),
    ("mais_vendidos", "Mais vendidos"),
)


def _discount_amount_expr():
    """Expressão SQL do desconto monetário (espelha Product.discount_amount)."""
    return Case(
        When(discount_type=Product.DiscountType.PERCENT, then=F("price") * F("discount_value") / Value(100)),
        When(discount_type=Product.DiscountType.FIXED, then=Least(F("discount_value"), F("price"))),
        default=Value(0),
        output_field=DecimalField(max_digits=10, decimal_places=2),
    )


def _active_products():
    return (
        Product.objects.filter(is_active=True)
        .select_related("category")
        .prefetch_related("images")
        .annotate(final_price_annotation=F("price") - _discount_amount_expr())
    )


def home(request):
    banners = Banner.objects.filter(is_active=True).order_by("order", "id")
    categories = Category.objects.filter(is_active=True)
    reserved = get_reserved_map()

    featured = _active_products().filter(is_featured=True)[:8]
    promos = _active_products().filter(discount_type__in=[Product.DiscountType.PERCENT, Product.DiscountType.FIXED])[:8]

    for product in list(featured) + list(promos):
        product.status = product.stock_status(reserved=reserved.get(product.pk, 0))

    return render(
        request,
        "catalog/home.html",
        {
            "banners": banners,
            "categories": categories,
            "featured_products": featured,
            "promo_products": promos,
            "sort_options": SORT_OPTIONS,
        },
    )


class ProductListView(ListView):
    template_name = "catalog/product_list.html"
    context_object_name = "products"
    paginate_by = PRODUCTS_PER_PAGE

    def get_queryset(self):
        from django.db.models import Sum, Subquery

        qs = _active_products()
        params = self.request.GET

        search = params.get("q", "").strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(short_description__icontains=search)
                | Q(description__icontains=search)
                | Q(category__name__icontains=search)
            )

        category_slug = params.get("categoria", "").strip()
        if category_slug:
            qs = qs.filter(category__slug=category_slug, category__is_active=True)

        min_price = params.get("preco_min", "").strip()
        max_price = params.get("preco_max", "").strip()
        try:
            if min_price:
                qs = qs.filter(final_price_annotation__gte=Decimal(min_price.replace(",", ".")))
            if max_price:
                qs = qs.filter(final_price_annotation__lte=Decimal(max_price.replace(",", ".")))
        except InvalidOperation:
            pass

        if params.get("promocao"):
            qs = qs.exclude(discount_type=Product.DiscountType.NONE)
        if params.get("destaque"):
            qs = qs.filter(is_featured=True)

        availability = params.get("disponibilidade", "").strip()
        if availability == "disponivel":
            qs = qs.filter(Q(stock__gt=0) | Q(allow_backorder=True))
        elif availability == "sob_encomenda":
            qs = qs.filter(stock__lte=0, allow_backorder=True)

        sort = params.get("ordenar", "relevancia")
        if sort == "menor_preco":
            return qs.order_by("final_price_annotation", "name")
        if sort == "maior_preco":
            return qs.order_by("-final_price_annotation", "name")
        if sort == "recentes":
            return qs.order_by("-created_at")
        if sort == "mais_vendidos":
            sold = OrderItem.objects.values("product_id").annotate(total=Sum("quantity"))
            sold_map = {row["product_id"]: row["total"] for row in sold}
            # Ordenação por vendas em Python preserva a paginação via lista ordenada.
            products = list(qs)
            products.sort(key=lambda p: sold_map.get(p.pk, 0), reverse=True)
            return products
        return qs.order_by("-is_featured", "-created_at", "name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reserved = get_reserved_map()
        for product in context["products"]:
            product.status = product.stock_status(reserved=reserved.get(product.pk, 0))
        context["categories"] = Category.objects.filter(is_active=True)
        category_slug = self.request.GET.get("categoria", "").strip()
        context["active_category"] = Category.objects.filter(slug=category_slug, is_active=True).first()
        context["sort_options"] = SORT_OPTIONS
        context["current_params"] = self.request.GET
        return context


class ProductDetailView(DetailView):
    template_name = "catalog/product_detail.html"
    context_object_name = "product"

    def get_queryset(self):
        return _active_products()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        reserved = get_reserved_map(exclude_session=self.request.session.session_key)
        product.status = product.stock_status(reserved=reserved.get(product.pk, 0))
        product.reserved_others = reserved.get(product.pk, 0)
        context["related_products"] = (
            _active_products().filter(category=product.category).exclude(pk=product.pk)[:4]
        )
        return context


def robots_txt(request):
    from django.contrib.sitemaps.views import sitemap as sitemap_view

    lines = ["User-agent: *", "Disallow: /painel/", "Disallow: /django-admin/", "Allow: /"]
    return render(request, "robots.txt", {"lines": lines}, content_type="text/plain")


def privacy(request):
    return render(request, "catalog/privacy.html")
