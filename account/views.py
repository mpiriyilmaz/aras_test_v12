"""
Bu dosya: account/views.py
--------------------------------
Giriş ekranını (login) çalıştıran view.
Mantık:
- GET     -> Boş form göster.
- POST    -> Formu doğrula; şifre doğru ise oturum aç ve yönlendir.
"""

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, get_user_model
from .forms import LoginForm


def login_request(request):
    # Zaten giriş yapılmışsa anasayfaya gönder
    if request.user.is_authenticated:
        return redirect("index")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            # E-posta benzersiz olduğu için tek bir kullanıcı döner
            User = get_user_model()
            user_obj = User.objects.filter(email=email).first()

            if not user_obj:
                # Normalde buraya düşmez; form.clean_email zaten kontrol ediyor.
                form.add_error("email", "Bu e-posta ile kullanıcı bulunamadı.")
                return render(request, "account/login.html", {"form": form})

            # Django authenticate kullanıcı adı (username) ister
            user = authenticate(request, username=user_obj.username, password=password)

            if user is not None:
                login(request, user)
                # "remember_me" seçili değilse, oturum tarayıcı kapanınca bitsin:
                if not form.cleaned_data.get("remember_me"):
                    request.session.set_expiry(0)
                return redirect("index")

            # Şifre yanlışsa
            form.add_error(None, "E-posta doğru ama şifre hatalı.")
        # Form geçersizse aynı sayfayı hatalarla göster
        return render(request, "account/login.html", {"form": form})

    # GET -> boş form
    form = LoginForm()
    return render(request, "account/login.html", {"form": form})

