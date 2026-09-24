from django.urls import path

from . import views

app_name = 'subscriptions'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('subscriptions/', views.subscription_list, name='list'),
    path('subscriptions/new/', views.subscription_create, name='create'),
    path('subscriptions/<int:pk>/', views.subscription_detail, name='detail'),
    path('subscriptions/<int:pk>/edit/', views.subscription_update, name='update'),
    path('subscriptions/<int:pk>/delete/', views.subscription_delete, name='delete'),
    path('subscriptions/<int:pk>/status/<str:status>/', views.subscription_change_status, name='change_status'),
    path('subscriptions/<int:pk>/pay/', views.subscription_pay_now, name='pay_now'),
    path('calendar/', views.payment_calendar, name='calendar'),
    path('payments/', views.payment_list, name='payments'),
    path('payments/new/', views.payment_create, name='payment_create'),
    path('payments/<int:pk>/edit/', views.payment_update, name='payment_update'),
    path('payments/<int:pk>/delete/', views.payment_delete, name='payment_delete'),
    path('notifications/', views.notification_list, name='notifications'),
    path('notifications/<int:pk>/read/', views.notification_read, name='notification_read'),
    path('notifications/read-all/', views.notification_read_all, name='notification_read_all'),
]
