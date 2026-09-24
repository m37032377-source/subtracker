from django.contrib import admin

from .models import Category, Currency, Notification, Payment, Subscription


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'symbol', 'rate_to_rub', 'updated_at')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'color')
    search_fields = ('name',)


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'category', 'price', 'currency', 'billing_period', 'status', 'next_payment_date')
    list_filter = ('status', 'billing_period', 'category')
    search_fields = ('name', 'user__email')
    inlines = [PaymentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('subscription', 'amount', 'currency', 'amount_rub', 'paid_at', 'status')
    list_filter = ('status',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
