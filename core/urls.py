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
    path("health/", views.health_check, name="health"),
    path("health", views.health_check),
    path("ping/", views.health_check),
    path("telegram/webhook/", views.telegram_webhook, name="telegram_webhook"),
    path("telegram/webhook", views.telegram_webhook),
    path("telegram/setup-webhook/", views.setup_telegram_webhook_view, name="setup_telegram_webhook"),
    path("telegram/setup-webhook", views.setup_telegram_webhook_view),
]
