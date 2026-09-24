"""Автоматические тесты ключевой логики.  Запуск: python manage.py test"""
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

from . import services
from .models import Category, Currency, Notification, Payment, Subscription


class DateLogicTests(TestCase):
    def test_add_months_end_of_month(self):
        self.assertEqual(services.add_months(date(2026, 1, 31), 1), date(2026, 2, 28))
        self.assertEqual(services.add_months(date(2026, 11, 15), 3), date(2027, 2, 15))

    def test_next_billing_date(self):
        d = date(2026, 3, 10)
        self.assertEqual(services.next_billing_date(d, 'weekly'), date(2026, 3, 17))
        self.assertEqual(services.next_billing_date(d, 'quarterly'), date(2026, 6, 10))
        self.assertEqual(services.next_billing_date(d, 'yearly'), date(2027, 3, 10))


class SubscriptionLogicTests(TestCase):
    def setUp(self):
        self.rub = Currency.objects.create(code='RUB', name='Рубль', symbol='₽', rate_to_rub=1)
        self.usd = Currency.objects.create(code='USD', name='Доллар', symbol='$', rate_to_rub=Decimal('90'))
        self.category = Category.objects.create(name='Видео')
        self.user = User.objects.create_user('u@test.ru', 'pass12345word', default_currency=self.rub)
        self.other = User.objects.create_user('o@test.ru', 'pass12345word')

    def make_sub(self, **kwargs):
        data = dict(user=self.user, category=self.category, currency=self.rub, name='Сервис',
                    price=Decimal('300'), next_payment_date=timezone.localdate())
        data.update(kwargs)
        return Subscription.objects.create(**data)

    def test_monthly_cost_and_conversion(self):
        self.make_sub(price=Decimal('1200'), billing_period='yearly')     # 100 ₽ в месяц
        self.make_sub(price=Decimal('10'), currency=self.usd)             # 900 ₽ в месяц
        self.assertEqual(services.monthly_total(self.user), Decimal('1000.00'))

    def test_due_payments_are_created_and_date_moves(self):
        start = timezone.localdate() - timedelta(days=65)
        sub = self.make_sub(start_date=start, next_payment_date=start)
        created = services.process_due_payments(self.user)
        sub.refresh_from_db()
        self.assertEqual(created, 3)  # пропущены три ежемесячных списания
        self.assertGreater(sub.next_payment_date, timezone.localdate())
        self.assertEqual(Payment.objects.filter(subscription=sub).count(), 3)

    def test_payment_stores_rub_amount(self):
        sub = self.make_sub(currency=self.usd, price=Decimal('10'))
        payment = Payment.objects.create(subscription=sub, currency=self.usd, amount=Decimal('10'))
        self.assertEqual(payment.amount_rub, Decimal('900.00'))

    def test_upcoming_notification_is_not_duplicated(self):
        self.make_sub(next_payment_date=timezone.localdate() + timedelta(days=2))
        services.generate_notifications(self.user)
        services.generate_notifications(self.user)
        self.assertEqual(Notification.objects.filter(user=self.user, notification_type='upcoming').count(), 1)

    def test_user_cannot_open_foreign_subscription(self):
        foreign = self.make_sub(user=self.other)
        self.client.login(email='u@test.ru', password='pass12345word')
        response = self.client.get(reverse('subscriptions:detail', args=[foreign.pk]))
        self.assertEqual(response.status_code, 404)

    def test_regular_user_has_no_access_to_admin_panel(self):
        self.client.login(email='u@test.ru', password='pass12345word')
        response = self.client.get(reverse('management_panel:home'))
        self.assertRedirects(response, reverse('subscriptions:dashboard'), fetch_redirect_response=False)
