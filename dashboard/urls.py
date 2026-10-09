from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="dashboard/login.html", redirect_authenticated_user=True),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", views.home, name="home"),
    path("pedidos/", views.order_list, name="order_list"),
    path("pedidos/<int:order_id>/", views.order_detail, name="order_detail"),
    path("produtos/", views.product_list, name="product_list"),
    path("desconto-em-massa/", views.mass_discount, name="mass_discount"),
    path("relatorios/", views.reports, name="reports"),
]
