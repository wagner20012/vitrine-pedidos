from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap as sitemap_view
from django.urls import include, path
from django.views.static import serve as static_serve

from catalog.sitemaps import sitemaps

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("painel/", include("dashboard.urls")),
    path("", include("catalog.urls")),
    path("carrinho/", include("cart.urls")),
    path("pedido/", include("orders.urls")),
    path("sitemap.xml", sitemap_view, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
]

if settings.DEBUG:
    urlpatterns += [
        path("media/<path:path>", static_serve, {"document_root": settings.MEDIA_ROOT}),
    ]
