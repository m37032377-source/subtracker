"""Расчёты для модуля аналитики расходов.

Все суммы хранятся в платежах в двух видах: в валюте списания (amount) и в
рублях (amount_rub). Для агрегирования используется amount_rub, а затем
результат переводится в основную валюту пользователя делением на её курс.
"""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth

from subscriptions.models import Payment, Subscription
from subscriptions.services import add_months, convert, get_user_currency


@dataclass
class Period:
    date_from: date
    date_to: date

    @property
    def days(self) -> int:
        return (self.date_to - self.date_from).days + 1

    def previous(self) -> 'Period':
        """Предыдущий период такой же длины — для сравнения динамики."""
        length = self.date_to - self.date_from
        prev_to = self.date_from - timedelta(days=1)
        return Period(prev_to - length, prev_to)


def default_period(today: date) -> Period:
    """По умолчанию — последние 12 месяцев, включая текущий."""
    return Period(add_months(today.replace(day=1), -11), today)


def paid_payments(user, period: Period):
    return Payment.objects.filter(
        subscription__user=user,
        status=Payment.Status.PAID,
        paid_at__range=(period.date_from, period.date_to),
    )


def to_user_currency(amount_rub, currency) -> Decimal:
    amount_rub = Decimal(amount_rub or 0)
    return (amount_rub / currency.rate_to_rub).quantize(Decimal('0.01'))


def summary(user, period: Period) -> dict:
    """Итоговые показатели за период и сравнение с предыдущим периодом."""
    currency = get_user_currency(user)
    current = paid_payments(user, period).aggregate(total=Sum('amount_rub'), count=Count('id'))
    previous = paid_payments(user, period.previous()).aggregate(total=Sum('amount_rub'))

    total = to_user_currency(current['total'], currency)
    prev_total = to_user_currency(previous['total'], currency)
    months = max(Decimal(period.days) / Decimal('30.44'), Decimal('1'))

    change_percent = None
    if prev_total:
        change_percent = round((total - prev_total) / prev_total * 100, 1)

    return {
        'currency': currency,
        'total': total,
        'payments_count': current['count'],
        'avg_per_month': (total / months).quantize(Decimal('0.01')),
        'prev_total': prev_total,
        'change_percent': change_percent,
    }


def by_category(user, period: Period) -> list[dict]:
    """Фактические расходы по категориям (для круговой диаграммы)."""
    currency = get_user_currency(user)
    rows = (
        paid_payments(user, period)
        .values('subscription__category__name', 'subscription__category__color')
        .annotate(total=Sum('amount_rub'))
        .order_by('-total')
    )
    return [
        {
            'name': r['subscription__category__name'],
            'color': r['subscription__category__color'],
            'total': to_user_currency(r['total'], currency),
        }
        for r in rows
    ]


def by_month(user, period: Period) -> list[dict]:
    """Расходы по месяцам (для столбчатой диаграммы). Месяцы без платежей
    заполняются нулями, чтобы на графике не было «дыр»."""
    currency = get_user_currency(user)
    rows = (
        paid_payments(user, period)
        .annotate(month=TruncMonth('paid_at'))
        .values('month')
        .annotate(total=Sum('amount_rub'))
    )
    totals = {r['month'].strftime('%Y-%m'): r['total'] for r in rows}

    result = []
    month = period.date_from.replace(day=1)
    while month <= period.date_to:
        key = month.strftime('%Y-%m')
        result.append({'month': key, 'total': to_user_currency(totals.get(key), currency)})
        month = add_months(month, 1)
    return result


def top_subscriptions(user, period: Period, limit: int = 5) -> list[dict]:
    """Самые затратные подписки за период."""
    currency = get_user_currency(user)
    rows = (
        paid_payments(user, period)
        .values('subscription__id', 'subscription__name', 'subscription__category__name')
        .annotate(total=Sum('amount_rub'), count=Count('id'))
        .order_by('-total')[:limit]
    )
    return [
        {
            'id': r['subscription__id'],
            'name': r['subscription__name'],
            'category': r['subscription__category__name'],
            'count': r['count'],
            'total': to_user_currency(r['total'], currency),
        }
        for r in rows
    ]


def planned_by_category(user) -> list[dict]:
    """Плановая месячная нагрузка по категориям на основе активных подписок."""
    currency = get_user_currency(user)
    totals: dict[str, dict] = {}
    for sub in user.subscriptions.select_related('category', 'currency').filter(
        status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIAL]
    ):
        item = totals.setdefault(sub.category.name, {'name': sub.category.name, 'total': Decimal('0')})
        item['total'] += convert(sub.monthly_cost, sub.currency, currency)
    return sorted(totals.values(), key=lambda x: x['total'], reverse=True)
