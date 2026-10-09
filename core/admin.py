from django.contrib import admin

from .models import AuditLog, Banner, StoreConfiguration


@admin.register(StoreConfiguration)
class StoreConfigurationAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Loja", {"fields": ("store_name", "tagline")}),
        (
            "Aparência",
            {"fields": ("logo", "favicon", "primary_color", "accent_color")},
        ),
        (
            "Contato",
            {
                "fields": (
                    "phone",
                    "email",
                    "address",
                    "instagram",
                    "business_hours",
                    "service_message",
                )
            },
        ),
        (
            "WhatsApp",
            {
                "fields": ("whatsapp_active", "whatsapp_number", "whatsapp_message"),
                "description": "O número não deve ser fixado no código: configure aqui.",
            },
        ),
        (
            "Estoque e pedidos",
            {"fields": ("allow_order_when_zero_stock", "reservation_minutes")},
        ),
    )

    def has_add_permission(self, request):
        return not StoreConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "is_active", "created_at")
    list_editable = ("order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title", "subtitle")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "user", "object_type", "object_repr", "created_at")
    list_filter = ("action", "object_type")
    search_fields = ("action", "object_repr", "details")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
