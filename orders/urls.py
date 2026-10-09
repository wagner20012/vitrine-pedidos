from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("confirmacao/", views.confirmation, name="confirmation"),
    path("<int:order_id>/whatsapp/", views.whatsapp_retry, name="whatsapp_retry"),
]
