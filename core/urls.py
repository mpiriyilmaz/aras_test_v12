"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView  # <-- EKLE

urlpatterns = [
    path("admin/", admin.site.urls),

    # /index/ -> tablo1duzeltme:ozet (vendor/yıl default)
    # login olduğun zaman yönlendirilecek sayfa belirliyoruz 
    # account/views.py/ def login_request(request): fonksiyonundan yönlendiriyoruz
    path(
        "index/",
        RedirectView.as_view(
            pattern_name="tablo1duzeltme:ozet",
            permanent=False
        ),
        {"vendor": "inavitas", "year": 2022},   # <-- default hedef
        name="index",
    ),

    # Login & logout (account.urls içinde name="login" mevcut)
    path("", include("account.urls")),

    # Diğer app’ler
    path("rapor/", include(("rapor.urls", "rapor"), namespace="rapor")),
    path("tablo1duzeltme/", include(("tablo1duzeltme.urls", "tablo1duzeltme"), namespace="tablo1duzeltme")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
