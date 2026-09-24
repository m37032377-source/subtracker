"""Команда загрузки демонстрационных данных:  python manage.py load_demo_data [--reset]"""
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from subscriptions import services
from subscriptions.models import Category, Currency, Notification, Payment, Subscription

DEMO_PASSWORD = 'demo12345'

CURRENCIES = [
    ('RUB', 'Российский рубль', '₽', '1'),
    ('USD', 'Доллар США', '$', '92.50'),
    ('EUR', 'Евро', '€', '100.20'),
]

CATEGORIES = [
    ('Видео и кино', 'Онлайн-кинотеатры и стриминг', '#ef4444', 'bi-film'),
    ('Музыка', 'Музыкальные сервисы', '#10b981', 'bi-music-note-beamed'),
    ('Облачные хранилища', 'Хранение файлов и резервные копии', '#3b82f6', 'bi-cloud'),
    ('Работа и продуктивность', 'Профессиональные инструменты', '#8b5cf6', 'bi-briefcase'),
    ('Образование', 'Курсы и обучающие платформы', '#f59e0b', 'bi-mortarboard'),
    ('Игры', 'Игровые подписки', '#ec4899', 'bi-controller'),
    ('Новости и чтение', 'Книги, пресса, медиа', '#14b8a6', 'bi-book'),
]

# (сервис, категория, цена, валюта, период, статус, сколько дней назад начата, заметка)
MAIN_USER_SUBSCRIPTIONS = [
    ('Кинопоиск', 'Видео и кино', '399', 'RUB', 'monthly', 'active', 720, 'Семейный доступ'),
    ('Яндекс Плюс', 'Музыка', '299', 'RUB', 'monthly', 'active', 650, ''),
    ('ChatGPT Plus', 'Работа и продуктивность', '20', 'USD', 'monthly', 'active', 420, 'Для учёбы и работы'),
    ('Notion Plus', 'Работа и продуктивность', '96', 'USD', 'yearly', 'active', 480, ''),
    ('Яндекс 360', 'Облачные хранилища', '199', 'RUB', 'monthly', 'active', 600, '200 ГБ'),
    ('JetBrains All Products', 'Работа и продуктивность', '299', 'EUR', 'yearly', 'active', 150, 'Студенческая скидка закончилась'),
    ('Литрес', 'Новости и чтение', '399', 'RUB', 'monthly', 'paused', 500, 'Поставил на паузу летом'),
    ('Duolingo Super', 'Образование', '1690', 'RUB', 'quarterly', 'active', 560, ''),
    ('Xbox Game Pass', 'Игры', '14.99', 'USD', 'monthly', 'trial', 5, 'Пробный месяц'),
    ('Okko', 'Видео и кино', '399', 'RUB', 'monthly', 'cancelled', 610, 'Отменил — дублирует Кинопоиск'),
    ('Spotify Premium', 'Музыка', '10.99', 'EUR', 'monthly', 'active', 300, ''),
]

SECOND_USER_SUBSCRIPTIONS = [
    ('Кинопоиск', 'Видео и кино', '399', 'RUB', 'monthly', 'active', 200, ''),
    ('Яндекс Плюс', 'Музыка', '299', 'RUB', 'monthly', 'active', 180, ''),
    ('Skillbox', 'Образование', '4900', 'RUB', 'monthly', 'active', 90, 'Курс по дизайну'),
    ('iCloud+', 'Облачные хранилища', '149', 'RUB', 'monthly', 'active', 300, ''),
]


class Command(BaseCommand):
    help = 'Загружает демонстрационные данные (валюты, категории, пользователи, подписки, платежи).'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Удалить существующие данные перед загрузкой')

    @transaction.atomic
    def handle(self, *args, **options):
        if options['reset']:
            Notification.objects.all().delete()
            Payment.objects.all().delete()
            Subscription.objects.all().delete()
            User.objects.all().delete()
            Category.objects.all().delete()
            Currency.objects.all().delete()

        currencies = {}
        for code, name, symbol, rate in CURRENCIES:
            currencies[code], _ = Currency.objects.update_or_create(
                code=code, defaults={'name': name, 'symbol': symbol, 'rate_to_rub': Decimal(rate)}
            )
        categories = {}
        for name, description, color, icon in CATEGORIES:
            categories[name], _ = Category.objects.update_or_create(
                name=name, defaults={'description': description, 'color': color, 'icon': icon}
            )

        admin = self._user('admin@example.com', 'Анна', 'Смирнова', User.Role.ADMIN, currencies['RUB'])
        admin.is_superuser = True
        admin.save()
        main = self._user('user@example.com', 'Михаил', 'Иванов', User.Role.USER, currencies['RUB'],
                          budget=Decimal('5000'))
        second = self._user('maria@example.com', 'Мария', 'Кузнецова', User.Role.USER, currencies['RUB'])

        self._subscriptions(main, MAIN_USER_SUBSCRIPTIONS, categories, currencies)
        self._subscriptions(second, SECOND_USER_SUBSCRIPTIONS, categories, currencies)

        for user in (main, second):
            services.refresh_user_state(user)

        self.stdout.write(self.style.SUCCESS(
            f'Демо-данные загружены. Вход: admin@example.com / user@example.com / maria@example.com, пароль {DEMO_PASSWORD}'
        ))

    def _user(self, email, first, last, role, currency, budget=None):
        user, created = User.objects.get_or_create(email=email, defaults={
            'first_name': first, 'last_name': last, 'role': role,
            'default_currency': currency, 'monthly_budget': budget,
        })
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save()
        return user

    def _subscriptions(self, user, rows, categories, currencies):
        today = timezone.localdate()
        for name, category, price, code, period, status, days_ago, notes in rows:
            if user.subscriptions.filter(name=name).exists():
                continue
            start = today - timedelta(days=days_ago)
            sub = Subscription(
                user=user, name=name, category=categories[category], currency=currencies[code],
                price=Decimal(price), billing_period=period, status=status, start_date=start,
                next_payment_date=start, notes=notes, remind_days_before=7,
            )
            if status == Subscription.Status.TRIAL:
                sub.trial_end_date = start + timedelta(days=30)
                sub.next_payment_date = sub.trial_end_date
                sub.save()
                continue

            # История платежей: от даты начала до сегодняшнего дня (для отменённых
            # и приостановленных — до момента остановки)
            stop_date = today if status == Subscription.Status.ACTIVE else today - timedelta(days=days_ago // 3)
            payments = []
            date = start
            while date <= stop_date:
                payments.append(date)
                date = services.next_billing_date(date, period)
            sub.next_payment_date = date
            sub.save()
            for index, paid_at in enumerate(payments):
                # Цена сервиса выросла пару месяцев назад — это видно в аналитике
                amount = sub.price
                if name == 'Кинопоиск' and paid_at < today - timedelta(days=90):
                    amount = Decimal('299')
                Payment.objects.create(
                    subscription=sub, currency=sub.currency, amount=amount, paid_at=paid_at,
                    status=Payment.Status.PAID,
                    comment='Первое списание' if index == 0 else '',
                )
