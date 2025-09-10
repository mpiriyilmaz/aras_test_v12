from django.urls import path
from .views import home

app_name = "duzeltme"

urlpatterns = [
    path("", home, name="home"),
]