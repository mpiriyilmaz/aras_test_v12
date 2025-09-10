"""
Bu dosya: account/urls.py
--------------------------------
Login sayfası için URL eşlemesi.
"""

from django.urls import path
from .views import login_request
from django.contrib.auth import views as auth_views


# login ve logout linkleri eklenir
urlpatterns = [
    path("", login_request, name="login"),  # örn. / (root) login’e gitsin
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),  # NEW
]

