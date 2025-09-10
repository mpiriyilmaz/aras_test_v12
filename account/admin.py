"""
Bu dosya: account/admin.py
--------------------------------
Django admin'inde kendi User modelimizi nasıl göstereceğimizi ayarlıyoruz.

Önemli değişiklik:
- Artık İLÇE alanı yok; sadece İL var.
- Yeni kullanıcı eklerken varsayılan bir/kaç grubu otomatik seçili getiriyoruz.
"""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

User = get_user_model()

# Yeni kullanıcı oluşturulurken otomatik seçilecek grup(lar)
DEFAULT_USER_GROUPS = ["Aras Muhendis"]


# ---- Admin formları ----
class MyUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # İL’i zorunlu yap (modelde blank=True ama admin/form düzeyinde required)
        self.fields["il"].required = True


class MyUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        # İLÇE yok; yalnızca İL var
        fields = ("username", "email", "first_name", "last_name", "il")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["il"].required = True


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = MyUserChangeForm
    add_form = MyUserCreationForm

    # Liste görünümlerinde hangi sütunlar gözüksün?
    list_display = ("username", "first_name", "last_name", "email", "il", "is_staff")
    list_filter = ("il", "is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "first_name", "last_name", "email", "il")
    ordering = ("id",)
    filter_horizontal = ("groups", "user_permissions")

    # Detay sayfasında alan grupları
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Kişisel Bilgiler"), {"fields": ("first_name", "last_name", "email", "il")}),
        (_("İzinler"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Önemli Tarihler"), {"fields": ("last_login", "date_joined")}),
    )

    # "Kullanıcı ekle" formunda gözükecek alanlar
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username", "email", "first_name", "last_name", "il",
                "password1", "password2",
                "is_active", "is_staff", "is_superuser", "groups",
            ),
        }),
    )

    # Yeni kullanıcı formu açıldığında varsayılan grupları seçili getir
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None and "groups" in form.base_fields and DEFAULT_USER_GROUPS:
            from django.contrib.auth.models import Group
            default_ids = list(
                Group.objects.filter(name__in=DEFAULT_USER_GROUPS).values_list("pk", flat=True)
            )
            form.base_fields["groups"].initial = default_ids
        return form

    # Kayıttan sonra da garanti olsun diye varsayılan grupları ekle
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change and DEFAULT_USER_GROUPS:
            from django.contrib.auth.models import Group
            defaults = list(Group.objects.filter(name__in=DEFAULT_USER_GROUPS))
            if defaults:
                obj.groups.add(*defaults)

    # Not: İLÇE tamamen kaldırıldığı için hiçbir ekstra JS, JSON endpoint vb. gerek yok.

