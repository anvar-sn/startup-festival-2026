from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("royxatdan-otish/", views.register, name="register"),
    path("register/", views.register),
    path("ariza/", views.register),
    path("apply/", views.register),
    path("muvaffaqiyat/<str:number>/", views.success, name="success"),
    path("holat/", views.status, name="status"),
    path("status/", views.status),
    path("qr/<str:number>.png", views.qr, name="qr"),
    path("export-excel/", views.export_excel_view, name="export_excel"),
]
