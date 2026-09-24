"""Бизнес-логика управления подписками.

Функции вынесены из представлений (views), чтобы их можно было повторно
использовать: на страницах сайта, в команде управления и в тестах.
"""
import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import Currency, Notification, Payment, Subscription


def format_money(value) -> str:
    """12345.6 -> '12 345,60' — формат сумм для текстов уведомлений."""
    return f'{Decimal(value):,.2f}'.replace(',', ' ').replace('.', ',')


def add_months(value: date, months: int) -> date:
    """Прибавляет к дате N месяцев с учётом разной длины месяцев.

    Пример: 31 января + 1 месяц = 28 (29) февраля.
    """
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def next_billing_date(current: date, period: str) -> date:
    """Возвращает дату следующего списания для заданного периода оплаты."""
    if period == Subscription.BillingPeriod.WEEKLY:
        return current + timedelta(weeks=1)
    if period == Subscription.BillingPeriod.MONTHLY:
        return add_months(current, 1)
    if period == Subscription.BillingPeriod.QUARTERLY:
        return add_months(current, 3)
    if period == Subscription.BillingPeriod.YEARLY:
        return add_months(current, 12)
    raise ValueError(f'Неизвестный период оплаты: {period}')


def convert(amount: Decimal, from_currency: Currency, to_currency: Currency) -> Decimal:
    """Пересчитывает сумму между валютами через курс к рублю."""
    if from_currency.pk == to_currency.pk:
        return amount
    in_rub = amount * from_currency.rate_to_rub
    return (in_rub / to_currency.rate_to_rub).quantize(Decimal('0.01'))


def get_user_currency(user) -> Currency:
    """Основная валюта пользователя (по умолчанию — рубль)."""
    if user.default_currency_id:
        return user.default_currency
    return Currency.objects.get_or_create(
        code='RUB', defaults={'name': 'Российский рубль', 'symbol': '₽', 'rate_to_rub': Decimal('1')}
    )[0]


def monthly_total(user, currency: Currency | None = None) -> Decimal:
    """Суммарная приведённая стоимость всех оплачиваемых подписок за месяц."""
    currency = currency or get_user_currency(user)
    total = Decimal('0')
    subscriptions = user.subscriptions.select_related('currency').filter(
        status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIAL]
    )
    for sub in subscriptions:
        total += convert(sub.monthly_cost, sub.currency, currency)
    return total.quantize(Decimal('0.01'))


@transaction.atomic
def process_due_payments(user, today: date | None = None) -> int:
    """Автоматически фиксирует списания, дата которых уже наступила.

    Для каждой оплачиваемой подписки, у которой next_payment_date <= сегодня,
    создаётся запись Payment, а дата следующего списания сдвигается на
    один период вперёд. Цикл while нужен, если пользователь долго не заходил
    и пропущено несколько периодов. Функция возвращает число созданных платежей.
    """
    today = today or timezone.localdate()
    created = 0
    due = user.subscriptions.select_related('currency').filter(
        status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIAL],
        next_payment_date__lte=today,
    )
    for sub in due:
        while sub.next_payment_date <= today:
            # Пробный период: первое списание происходит только после его окончания
            if sub.status == Subscription.Status.TRIAL:
                if sub.trial_end_date and sub.trial_end_date > sub.next_payment_date:
                    sub.next_payment_date = sub.trial_end_date
                    continue
                sub.status = Subscription.Status.ACTIVE
            Payment.objects.create(
                subscription=sub,
                currency=sub.currency,
                amount=sub.price,
                paid_at=sub.next_payment_date,
                status=Payment.Status.PAID,
                comment='Автоматическое списание по расписанию',
            )
            Notification.objects.get_or_create(
                user=user,
                subscription=sub,
                notification_type=Notification.Type.PAYMENT,
                event_date=sub.next_payment_date,
                defaults={
                    'title': f'Списание: {sub.name}',
                    'message': f'Списано {sub.price} {sub.currency.symbol} за подписку «{sub.name}».',
                },
            )
            sub.next_payment_date = next_billing_date(sub.next_payment_date, sub.billing_period)
            created += 1
        sub.save(update_fields=['next_payment_date', 'status', 'updated_at'])
    return created


def generate_notifications(user, today: date | None = None) -> int:
    """Создаёт напоминания о скорых списаниях, окончании пробного периода
    и превышении месячного бюджета. Повторы исключаются уникальным
    ограничением модели Notification и методом get_or_create."""
    today = today or timezone.localdate()
    created = 0
    subscriptions = user.subscriptions.select_related('currency').filter(
        status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIAL]
    )
    for sub in subscriptions:
        days_left = (sub.next_payment_date - today).days
        if 0 <= days_left <= sub.remind_days_before:
            _, is_new = Notification.objects.get_or_create(
                user=user,
                subscription=sub,
                notification_type=Notification.Type.UPCOMING,
                event_date=sub.next_payment_date,
                defaults={
                    'title': f'Скоро списание: {sub.name}',
                    'message': (
                        f'{sub.next_payment_date:%d.%m.%Y} будет списано '
                        f'{sub.price} {sub.currency.symbol} за «{sub.name}».'
                    ),
                },
            )
            created += is_new
        if sub.status == Subscription.Status.TRIAL and sub.trial_end_date:
            trial_left = (sub.trial_end_date - today).days
            if 0 <= trial_left <= sub.remind_days_before:
                _, is_new = Notification.objects.get_or_create(
                    user=user,
                    subscription=sub,
                    notification_type=Notification.Type.TRIAL_END,
                    event_date=sub.trial_end_date,
                    defaults={
                        'title': f'Заканчивается пробный период: {sub.name}',
                        'message': (
                            f'Пробный период «{sub.name}» закончится {sub.trial_end_date:%d.%m.%Y}. '
                            f'Если сервис не нужен — отмените подписку заранее.'
                        ),
                    },
                )
                created += is_new

    # Контроль бюджета: одно уведомление на календарный месяц
    if user.monthly_budget:
        total = monthly_total(user)
        if total > user.monthly_budget:
            _, is_new = Notification.objects.get_or_create(
                user=user,
                subscription=None,
                notification_type=Notification.Type.BUDGET,
                event_date=today.replace(day=1),
                defaults={
                    'title': 'Превышен месячный бюджет',
                    'message': (
                        f'Подписки обходятся в {format_money(total)} в месяц при бюджете '
                        f'{format_money(user.monthly_budget)}. Проверьте, какие сервисы можно отключить.'
                    ),
                },
            )
            created += is_new
    return created


def refresh_user_state(user) -> None:
    """Вызывается при открытии главной страницы: фиксирует наступившие
    списания и формирует новые уведомления."""
    process_due_payments(user)
    generate_notifications(user)
