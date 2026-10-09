from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.home, name="home"),
    path("produtos/", views.ProductListView.as_view(), name="product_list"),
    path("produto/<slug:slug>/", views.ProductDetailView.as_view(), name="product_detail"),
    path("privacidade/", views.privacy, name="privacy"),
    path("robots.txt", views.robots_txt, name="robots"),
]
