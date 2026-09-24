from django.urls import path

from . import views

app_name = 'analytics'

urlpatterns = [
    path('', views.analytics_dashboard, name='dashboard'),
    path('export/csv/', views.export_csv, name='export_csv'),
    path('export/xlsx/', views.export_xlsx, name='export_xlsx'),
]
