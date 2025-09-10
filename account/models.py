"""
Bu dosya: account/models.py
--------------------------------
Kendi kullanıcı (User) modelimizi tanımlıyoruz.

Basit anlatım:
- Her kullanıcı bir "oyuncu kartı" gibi düşünülebilir.
- Bu kartta e-posta (tekil/benzersiz) ve hangi İL’de olduğu yazıyor.
- İLÇE alanını tamamen kaldırdık; artık sadece İL var.

Not: AbstractUser’dan miras alıyoruz, yani kullanıcı adı, şifre, son giriş,
personel/süper kullanıcı gibi alanlar zaten hazır geliyor.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models

from .constants import IL_CHOICES


class User(AbstractUser):
    """
    User modeli — "oyuncu kartımız"

    Eklediğimiz alanlar:
    1) email : E-posta (tekil). Aynı e-posta ile ikinci kullanıcı olamaz.
    2) il    : Kullanıcının ili (açılır listeden seçilir).
    """

    email = models.EmailField(
        unique=True,
        verbose_name="Email (tekil)",
        help_text="Aynı e-posta ile ikinci bir kullanıcı olamaz."
    )

    il = models.CharField(
        "İl",
        max_length=20,
        choices=IL_CHOICES,   # Sadece bu listedeki iller seçilebilir
        blank=True            # İstersen zorunlu yap: admin/form tarafında required=True veriyoruz
    )

    class Meta:
        verbose_name = "Kullanıcı"
        verbose_name_plural = "Kullanıcılar"

    def __str__(self):
        """
        Admin listesinde vb. kullanıcı nasıl görünsün?
        - Ad + Soyad varsa onu göster,
        - yoksa kullanıcı adını (username) göster.
        """
        return self.get_full_name() or self.username

