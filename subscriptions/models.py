"""Основные сущности предметной области: валюты, категории, подписки,
платежи (история расходов) и уведомления."""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Currency(models.Model):
    """Валюта и её курс к базовой валюте (рублю)."""

    code = models.CharField('Код', max_length=3, unique=True)  # ISO 4217: RUB, USD, EUR
    name = models.CharField('Название', max_length=50)
    symbol = models.CharField('Символ', max_length=5)
    rate_to_rub = models.DecimalField(
        'Курс к рублю', max_digits=12, decimal_places=4,
        default=Decimal('1'), validators=[MinValueValidator(Decimal('0.0001'))],
    )
    updated_at = models.DateTimeField('Обновлён', auto_now=True)

    class Meta:
        verbose_name = 'Валюта'
        verbose_name_plural = 'Валюты'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} ({self.symbol})'


class Category(models.Model):
    """Категория цифровых сервисов (справочник ведёт администратор)."""

    name = models.CharField('Название', max_length=60, unique=True)
    description = models.CharField('Описание', max_length=255, blank=True)
    color = models.CharField('Цвет на графиках', max_length=7, default='#4f46e5')
    icon = models.CharField('Иконка Bootstrap Icons', max_length=40, default='bi-grid')

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name


class Subscription(models.Model):
    """Цифровая подписка пользователя."""

    class BillingPeriod(models.TextChoices):
        WEEKLY = 'weekly', 'Еженедельно'
        MONTHLY = 'monthly', 'Ежемесячно'
        QUARTERLY = 'quarterly', 'Ежеквартально'
        YEARLY = 'yearly', 'Ежегодно'

    class Status(models.TextChoices):
        TRIAL = 'trial', 'Пробный период'
        ACTIVE = 'active', 'Активна'
        PAUSED = 'paused', 'Приостановлена'
        CANCELLED = 'cancelled', 'Отменена'

    # Сколько раз за год происходит списание — нужно для пересчёта в месяц/год
    PAYMENTS_PER_YEAR = {
        BillingPeriod.WEEKLY: Decimal('52'),
        BillingPeriod.MONTHLY: Decimal('12'),
        BillingPeriod.QUARTERLY: Decimal('4'),
        BillingPeriod.YEARLY: Decimal('1'),
    }

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='Владелец',
        on_delete=models.CASCADE, related_name='subscriptions',
    )
    category = models.ForeignKey(
        Category, verbose_name='Категория', on_delete=models.PROTECT, related_name='subscriptions',
    )
    currency = models.ForeignKey(
        Currency, verbose_name='Валюта', on_delete=models.PROTECT, related_name='subscriptions',
    )
    name = models.CharField('Сервис', max_length=100)
    price = models.DecimalField(
        'Стоимость', max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
    )
    billing_period = models.CharField(
        'Период оплаты', max_length=10, choices=BillingPeriod.choices, default=BillingPeriod.MONTHLY,
    )
    status = models.CharField('Статус', max_length=10, choices=Status.choices, default=Status.ACTIVE)
    start_date = models.DateField('Дата начала', default=timezone.localdate)
    next_payment_date = models.DateField('Следующее списание')
    trial_end_date = models.DateField('Окончание пробного периода', null=True, blank=True)
    remind_days_before = models.PositiveSmallIntegerField('Напомнить за (дней)', default=3)
    website = models.URLField('Сайт сервиса', blank=True)
    notes = models.TextField('Заметки', blank=True)
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    updated_at = models.DateTimeField('Изменена', auto_now=True)

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        ordering = ['next_payment_date', 'name']
        indexes = [models.Index(fields=['user', 'status', 'next_payment_date'])]

    def __str__(self):
        return f'{self.name} — {self.price} {self.currency.code}'

    def get_absolute_url(self):
        return reverse('subscriptions:detail', args=[self.pk])

    @property
    def is_billable(self) -> bool:
        """Списания происходят только у активных подписок и подписок на пробном периоде."""
        return self.status in (self.Status.ACTIVE, self.Status.TRIAL)

    @property
    def yearly_cost(self) -> Decimal:
        """Стоимость подписки за год в её собственной валюте."""
        return self.price * self.PAYMENTS_PER_YEAR[self.billing_period]

    @property
    def monthly_cost(self) -> Decimal:
        """Приведённая стоимость подписки за месяц в её собственной валюте."""
        return (self.yearly_cost / Decimal('12')).quantize(Decimal('0.01'))

    @property
    def days_until_payment(self) -> int:
        return (self.next_payment_date - timezone.localdate()).days


class Payment(models.Model):
    """Фактическое списание по подписке — запись в истории расходов."""

    class Status(models.TextChoices):
        PAID = 'paid', 'Оплачен'
        PENDING = 'pending', 'Ожидается'
        FAILED = 'failed', 'Ошибка'
        REFUNDED = 'refunded', 'Возврат'

    subscription = models.ForeignKey(
        Subscription, verbose_name='Подписка', on_delete=models.CASCADE, related_name='payments',
    )
    currency = models.ForeignKey(
        Currency, verbose_name='Валюта', on_delete=models.PROTECT, related_name='payments',
    )
    amount = models.DecimalField(
        'Сумма', max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))],
    )
    amount_rub = models.DecimalField(
        'Сумма в рублях', max_digits=12, decimal_places=2, editable=False, default=Decimal('0'),
    )
    paid_at = models.DateField('Дата списания', default=timezone.localdate)
    status = models.CharField('Статус', max_length=10, choices=Status.choices, default=Status.PAID)
    comment = models.CharField('Комментарий', max_length=255, blank=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Платёж'
        verbose_name_plural = 'Платежи'
        ordering = ['-paid_at', '-id']
        indexes = [models.Index(fields=['paid_at'])]

    def save(self, *args, **kwargs):
        # Фиксируем сумму в рублях по курсу на момент записи: история расходов
        # не должна меняться, если позже администратор обновит курс валюты.
        self.amount_rub = (self.amount * self.currency.rate_to_rub).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.subscription.name}: {self.amount} {self.currency.code} ({self.paid_at})'


class Notification(models.Model):
    """Уведомление пользователя внутри приложения."""

    class Type(models.TextChoices):
        UPCOMING = 'upcoming', 'Скорое списание'
        TRIAL_END = 'trial_end', 'Окончание пробного периода'
        PAYMENT = 'payment', 'Списание выполнено'
        BUDGET = 'budget', 'Превышение бюджета'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='Пользователь',
        on_delete=models.CASCADE, related_name='notifications',
    )
    subscription = models.ForeignKey(
        Subscription, verbose_name='Подписка', on_delete=models.CASCADE,
        related_name='notifications', null=True, blank=True,
    )
    notification_type = models.CharField('Тип', max_length=12, choices=Type.choices)
    title = models.CharField('Заголовок', max_length=150)
    message = models.TextField('Текст')
    event_date = models.DateField('Дата события', null=True, blank=True)
    is_read = models.BooleanField('Прочитано', default=False)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['is_read', '-created_at']
        # Одно и то же напоминание не должно создаваться повторно
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'subscription', 'notification_type', 'event_date'],
                name='unique_notification_per_event',
            )
        ]

    def __str__(self):
        return self.title
