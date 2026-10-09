from django.contrib import admin
from django.db.models import Exists, OuterRef
from django.db.models.functions import Lower

from orders.models import OrderItem

from .models import Category, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    fields = ("image", "alt_text", "order", "is_primary")
    readonly_fields = ("preview",)

    def preview(self, obj):
        from django.utils.html import format_html

        if obj.image:
            return format_html('<img src="{}" style="max-height:60px;border-radius:6px" />', obj.image.url)
        return "—"

    preview.short_description = "Prévia"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order", "is_active")
    list_editable = ("order", "is_active")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "price",
        "final_price_display",
        "stock",
        "is_featured",
        "is_active",
    )
    list_filter = ("is_active", "is_featured", "category", "discount_type")
    list_editable = ("is_featured", "is_active")
    search_fields = ("name", "short_description", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline]
    actions = ("activate", "deactivate")

    fieldsets = (
        ("Informações", {"fields": ("name", "slug", "category", "short_description", "description")}),
        ("Preços", {"fields": ("price", "discount_type", "discount_value")}),
        ("Estoque", {"fields": ("stock", "min_stock", "allow_backorder")}),
        ("Visibilidade", {"fields": ("is_featured", "is_active")}),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        has_orders = OrderItem.objects.filter(product=OuterRef("pk"))
        return qs.annotate(_has_orders=Exists(has_orders))

    @admin.display(description="Preço final")
    def final_price_display(self, obj):
        from core.utils import format_brl

        return format_brl(obj.final_price)

    @admin.action(description="Ativar produtos selecionados")
    def activate(self, request, queryset):
        queryset.update(is_active=True)
        from core.models import AuditLog

        AuditLog.log("Produtos ativados", user=request.user, details=f"{queryset.count()} produto(s)")

    @admin.action(description="Desativar produtos selecionados")
    def deactivate(self, request, queryset):
        queryset.update(is_active=False)
        from core.models import AuditLog

        AuditLog.log("Produtos desativados", user=request.user, details=f"{queryset.count()} produto(s)")

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return False
        return not OrderItem.objects.filter(product=obj).exists()

    def save_model(self, request, obj, form, change):
        old_price = old_stock = None
        if change:
            previous = Product.objects.get(pk=obj.pk)
            old_price, old_stock = previous.price, previous.stock
        super().save_model(request, obj, form, change)
        from core.models import AuditLog

        if change and old_price != obj.price:
            AuditLog.log(
                "Preço alterado", obj, request.user, f"{old_price} -> {obj.price}"
            )
        if change and old_stock != obj.stock:
            AuditLog.log(
                "Estoque alterado", obj, request.user, f"{old_stock} -> {obj.stock}"
            )
