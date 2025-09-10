"""
Bu dosya: account/forms.py
--------------------------------
Giriş (login) formu.
Kullanıcıdan e-posta ve şifre alıyoruz.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model


class LoginForm(forms.Form):
    """
    Çok basit bir form:
    - email    : Kullanıcının e-postası
    - password : Şifresi
    - remember_me : Beni hatırla (opsiyonel)
    """
    email = forms.EmailField(widget=forms.EmailInput(
        attrs={"class": "form-control form-control-user", "placeholder": "E-posta adresi"}))
    password = forms.CharField(widget=forms.PasswordInput(
        attrs={"class": "form-control form-control-user", "placeholder": "Şifre"}))
    remember_me = forms.BooleanField(required=False, initial=False,
                                     widget=forms.CheckboxInput(attrs={"class": "custom-control-input"}))

    def clean_email(self):
        """
        Burada girilen e-postayı gerçekten bir kullanıcı kullanıyor mu kontrol ederiz.
        """
        email = self.cleaned_data.get("email", "").strip()
        User = get_user_model()
        if not User.objects.filter(email=email).exists():
            raise ValidationError("Bu e-posta ile kayıtlı kullanıcı bulunamadı.")
        return email

