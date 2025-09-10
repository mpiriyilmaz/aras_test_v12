"""
Bu dosya: account/constants.py
--------------------------------
Burada yalnızca 'İL' seçeneklerini tutuyoruz. (Artık İLÇE yok.)
Admin/form açılır kutularında bu liste gösterilir.
"""

# Not: İstersen bu listeye yeni iller ekleyebilirsin.
IL_LIST = [
    "AĞRI",
    "ARDAHAN",
    "BAYBURT",
    "ERZİNCAN",
    "ERZURUM",
    "IĞDIR",
    "KARS",
    "ARAS",   # Özel amaçlı sanal/kurumsal bir bölge gibi düşün.
]

# Django 'choices' formatı (("AĞRI","AĞRI"), ...)
IL_CHOICES = [(x, x) for x in IL_LIST]

