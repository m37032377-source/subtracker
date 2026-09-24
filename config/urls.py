"""Главная таблица маршрутов проекта: подключает URL каждого приложения."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('django-admin/', admin.site.urls),  # стандартная админка Django
    path('accounts/', include('accounts.urls')),
    path('analytics/', include('analytics.urls')),
    path('panel/', include('management_panel.urls')),
    path('', include('subscriptions.urls')),
]
