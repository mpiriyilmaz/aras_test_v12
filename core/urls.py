# core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),

    # Giriş sonrası hedef (index) → duzeltme:home
    path(
        "index/",
        RedirectView.as_view(pattern_name="duzeltme:home", permanent=False),
        name="index",
    ),

    # Login/logout
    path("", include("account.urls")),

    # Düzeltme uygulaması
    path("duzeltme/", include(("duzeltme.urls", "duzeltme"), namespace="duzeltme")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
