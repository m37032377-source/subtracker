"""Представления (views) для работы с подписками, платежами и уведомлениями.

Все страницы доступны только авторизованным пользователям (@login_required).
Каждый запрос к БД фильтруется по request.user, поэтому пользователь видит и
изменяет только свои данные.
"""
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, Q, Sum, Value, When
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import services
from .forms import PaymentForm, SubscriptionFilterForm, SubscriptionForm
from .models import Notification, Payment, Subscription


# ---------------------------------------------------------------------------
# Главная страница (сводка)
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    user = request.user
    services.refresh_user_state(user)  # автосписания и напоминания

    today = timezone.localdate()
    currency = services.get_user_currency(user)
    active = user.subscriptions.filter(
        status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIAL]
    ).select_related('category', 'currency')

    month_total = services.monthly_total(user, currency)
    upcoming = active.filter(next_payment_date__range=(today, today + timedelta(days=14)))
    spent_this_month = Payment.objects.filter(
        subscription__user=user,
        status=Payment.Status.PAID,
        paid_at__year=today.year,
        paid_at__month=today.month,
    ).aggregate(total=Sum('amount_rub'))['total'] or 0

    budget_percent = None
    if user.monthly_budget:
        budget_percent = min(int(month_total / user.monthly_budget * 100), 100)

    context = {
        'currency': currency,
        'active_count': active.count(),
        'trial_count': active.filter(status=Subscription.Status.TRIAL).count(),
        'month_total': month_total,
        'year_total': month_total * 12,
        'spent_this_month': spent_this_month,
        'budget_percent': budget_percent,
        'upcoming': upcoming[:6],
        'recent_payments': Payment.objects.filter(subscription__user=user)
        .select_related('subscription', 'currency')[:5],
    }
    return render(request, 'subscriptions/dashboard.html', context)


# ---------------------------------------------------------------------------
# CRUD подписок
# ---------------------------------------------------------------------------

@login_required
def subscription_list(request):
    form = SubscriptionFilterForm(request.GET or None)
    # По умолчанию сначала показываем действующие подписки, затем остановленные
    queryset = request.user.subscriptions.select_related('category', 'currency').annotate(
        status_order=Case(
            When(status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIAL], then=Value(0)),
            default=Value(1), output_field=IntegerField(),
        )
    ).order_by('status_order', 'next_payment_date')

    if form.is_valid():
        data = form.cleaned_data
        if data['q']:
            queryset = queryset.filter(Q(name__icontains=data['q']) | Q(notes__icontains=data['q']))
        if data['category']:
            queryset = queryset.filter(category=data['category'])
        if data['status']:
            queryset = queryset.filter(status=data['status'])
        if data['period']:
            queryset = queryset.filter(billing_period=data['period'])
        if data['sort']:
            queryset = queryset.order_by(data['sort'])

    page = Paginator(queryset, 15).get_page(request.GET.get('page'))
    return render(request, 'subscriptions/subscription_list.html', {
        'form': form,
        'page_obj': page,
        'total_found': queryset.count(),
    })


@login_required
def subscription_detail(request, pk):
    subscription = get_object_or_404(
        Subscription.objects.select_related('category', 'currency'), pk=pk, user=request.user
    )
    payments = subscription.payments.select_related('currency')
    return render(request, 'subscriptions/subscription_detail.html', {
        'subscription': subscription,
        'payments': payments[:12],
        'total_paid': payments.filter(status=Payment.Status.PAID).aggregate(s=Sum('amount'))['s'] or 0,
    })


@login_required
def subscription_create(request):
    form = SubscriptionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        subscription = form.save(commit=False)
        subscription.user = request.user  # владелец задаётся на сервере, а не из формы
        subscription.save()
        messages.success(request, f'Подписка «{subscription.name}» добавлена.')
        return redirect(subscription)
    return render(request, 'subscriptions/subscription_form.html', {'form': form, 'is_new': True})


@login_required
def subscription_update(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    form = SubscriptionForm(request.POST or None, instance=subscription)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Изменения сохранены.')
        return redirect(subscription)
    return render(request, 'subscriptions/subscription_form.html', {
        'form': form, 'subscription': subscription, 'is_new': False,
    })


@login_required
def subscription_delete(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    if request.method == 'POST':
        name = subscription.name
        subscription.delete()  # платежи и уведомления удалятся каскадно
        messages.success(request, f'Подписка «{name}» удалена.')
        return redirect('subscriptions:list')
    return render(request, 'subscriptions/subscription_confirm_delete.html', {'subscription': subscription})


# ---------------------------------------------------------------------------
# Управление жизненным циклом подписки
# ---------------------------------------------------------------------------

# Допустимые переходы между статусами: из какого статуса в какие можно перейти
ALLOWED_TRANSITIONS = {
    Subscription.Status.TRIAL: {Subscription.Status.ACTIVE, Subscription.Status.CANCELLED},
    Subscription.Status.ACTIVE: {Subscription.Status.PAUSED, Subscription.Status.CANCELLED},
    Subscription.Status.PAUSED: {Subscription.Status.ACTIVE, Subscription.Status.CANCELLED},
    Subscription.Status.CANCELLED: {Subscription.Status.ACTIVE},
}


@login_required
@require_POST
def subscription_change_status(request, pk, status):
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    if status not in ALLOWED_TRANSITIONS.get(subscription.status, set()):
        messages.error(request, 'Такое изменение статуса недоступно.')
        return redirect(subscription)

    # При возобновлении дата списания не должна остаться в прошлом
    if status == Subscription.Status.ACTIVE:
        today = timezone.localdate()
        while subscription.next_payment_date < today:
            subscription.next_payment_date = services.next_billing_date(
                subscription.next_payment_date, subscription.billing_period
            )
    subscription.status = status
    subscription.save()
    messages.success(request, f'Статус изменён: {subscription.get_status_display().lower()}.')
    return redirect(subscription)


@login_required
@require_POST
def subscription_pay_now(request, pk):
    """Ручная отметка об оплате: создаёт платёж и сдвигает дату следующего списания."""
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    if not subscription.is_billable:
        messages.error(request, 'Нельзя отметить оплату у приостановленной или отменённой подписки.')
        return redirect(subscription)
    Payment.objects.create(
        subscription=subscription,
        currency=subscription.currency,
        amount=subscription.price,
        paid_at=timezone.localdate(),
        comment='Отмечено вручную',
    )
    subscription.next_payment_date = services.next_billing_date(
        subscription.next_payment_date, subscription.billing_period
    )
    subscription.save(update_fields=['next_payment_date', 'updated_at'])
    messages.success(request, 'Платёж записан, дата следующего списания обновлена.')
    return redirect(subscription)


@login_required
def payment_calendar(request):
    """Календарь ближайших списаний на 30 дней вперёд, сгруппированный по датам."""
    today = timezone.localdate()
    horizon = today + timedelta(days=30)
    events = []
    for sub in request.user.subscriptions.select_related('currency', 'category').filter(
        status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIAL]
    ):
        date = sub.next_payment_date
        while date <= horizon:  # еженедельные подписки попадут в календарь несколько раз
            if date >= today:
                events.append({'date': date, 'subscription': sub})
            date = services.next_billing_date(date, sub.billing_period)
    events.sort(key=lambda e: e['date'])

    grouped = {}
    for event in events:
        grouped.setdefault(event['date'], []).append(event['subscription'])
    return render(request, 'subscriptions/calendar.html', {
        'grouped': grouped.items(), 'today': today, 'horizon': horizon,
    })


# ---------------------------------------------------------------------------
# CRUD платежей (история расходов)
# ---------------------------------------------------------------------------

@login_required
def payment_list(request):
    payments = Payment.objects.filter(subscription__user=request.user).select_related(
        'subscription', 'subscription__category', 'currency'
    )
    subscription_id = request.GET.get('subscription')
    if subscription_id:
        payments = payments.filter(subscription_id=subscription_id)
    page = Paginator(payments, 15).get_page(request.GET.get('page'))
    return render(request, 'subscriptions/payment_list.html', {
        'page_obj': page,
        'subscriptions': request.user.subscriptions.order_by('name'),
        'selected': subscription_id,
        'total_rub': payments.filter(status=Payment.Status.PAID).aggregate(s=Sum('amount_rub'))['s'] or 0,
    })


@login_required
def payment_create(request):
    initial = {}
    if request.GET.get('subscription'):
        sub = get_object_or_404(Subscription, pk=request.GET['subscription'], user=request.user)
        initial = {'subscription': sub, 'amount': sub.price, 'currency': sub.currency}
    form = PaymentForm(request.POST or None, user=request.user, initial=initial)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Платёж добавлен в историю расходов.')
        return redirect('subscriptions:payments')
    return render(request, 'subscriptions/payment_form.html', {'form': form, 'is_new': True})


@login_required
def payment_update(request, pk):
    payment = get_object_or_404(Payment, pk=pk, subscription__user=request.user)
    form = PaymentForm(request.POST or None, instance=payment, user=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Платёж обновлён.')
        return redirect('subscriptions:payments')
    return render(request, 'subscriptions/payment_form.html', {'form': form, 'is_new': False})


@login_required
@require_POST
def payment_delete(request, pk):
    payment = get_object_or_404(Payment, pk=pk, subscription__user=request.user)
    payment.delete()
    messages.success(request, 'Платёж удалён.')
    return redirect('subscriptions:payments')


# ---------------------------------------------------------------------------
# Уведомления
# ---------------------------------------------------------------------------

@login_required
def notification_list(request):
    services.generate_notifications(request.user)
    notifications = request.user.notifications.select_related('subscription')
    return render(request, 'subscriptions/notifications.html', {
        'notifications': notifications[:50],
    })


@login_required
@require_POST
def notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    return redirect('subscriptions:notifications')


@login_required
@require_POST
def notification_read_all(request):
    updated = request.user.notifications.filter(is_read=False).update(is_read=True)
    messages.info(request, f'Отмечено как прочитанные: {updated}.')
    return redirect('subscriptions:notifications')
