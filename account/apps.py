"""
Bu dosya: account/apps.py
--------------------------------
Uygulama açıldığında (migrasyonlardan sonra) lazım olan varsayılan grupları
otomatik oluşturuyoruz.
"""

from django.apps import AppConfig
from django.db.models.signals import post_migrate

GROUP_NAMES = [
    "BT Admin",
    "Admin",
    "OMS Admin",
    "OMS Operator",
    "OMS Arsiv",
    "Aras Muhendis",
    "Aras Mudur",
]


def create_default_groups(sender, **kwargs):
    from django.contrib.auth.models import Group
    for name in GROUP_NAMES:
        Group.objects.get_or_create(name=name)


class AccountConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "account"

    def ready(self):
        # Migrasyonlardan SONRA bir kere çalışır; DB erişimi güvenlidir.
        post_migrate.connect(create_default_groups, sender=self)

