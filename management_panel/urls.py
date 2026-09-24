from django.urls import path

from . import views

app_name = 'management_panel'

urlpatterns = [
    path('', views.panel_home, name='home'),
    path('users/', views.user_list, name='users'),
    path('users/<int:pk>/edit/', views.user_update, name='user_update'),
    path('users/<int:pk>/toggle/', views.user_toggle_active, name='user_toggle'),
    path('<str:kind>/', views.reference_list, name='reference_list'),
    path('<str:kind>/new/', views.reference_edit, name='reference_create'),
    path('<str:kind>/<int:pk>/edit/', views.reference_edit, name='reference_update'),
    path('<str:kind>/<int:pk>/delete/', views.reference_delete, name='reference_delete'),
]
