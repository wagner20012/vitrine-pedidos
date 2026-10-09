from django.contrib import admin

from .models import Order, OrderItem, PaymentMethod, StockReservation


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "product_name", "unit_price", "discount_value", "unit_final_price", "quantity", "subtotal")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "is_active")
    list_editable = ("order", "is_active")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "customer_name", "customer_phone", "total", "payment_method_name", "status", "created_at")
    list_filter = ("status", "payment_method_name", "created_at")
    search_fields = ("number", "customer_name", "customer_phone")
    inlines = [OrderItemInline]
    date_hierarchy = "created_at"
    readonly_fields = ("number", "idempotency_key", "subtotal", "discount_total", "total", "payment_method_name", "created_at", "updated_at", "cancelled_at")

    def has_delete_permission(self, request, obj=None):
        # Nunca excluir pedidos: somente cancelamento lógico.
        return False


@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity", "status", "session_key", "created_at", "expires_at")
    list_filter = ("status",)

    def has_add_permission(self, request):
        return False
