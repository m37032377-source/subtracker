"""Административная панель: статистика системы, пользователи и справочники."""
from django.contrib import messages
from django.db.models import Count, ProtectedError, Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required
from accounts.models import User
from subscriptions.models import Category, Currency, Payment, Subscription

from .forms import CategoryForm, CurrencyForm, UserAdminForm


@admin_required
def panel_home(request):
    today = timezone.localdate()
    context = {
        'users_total': User.objects.count(),
        'users_active': User.objects.filter(is_active=True).count(),
        'new_users_month': User.objects.filter(
            date_joined__year=today.year, date_joined__month=today.month
        ).count(),
        'subscriptions_total': Subscription.objects.count(),
        'subscriptions_active': Subscription.objects.filter(status=Subscription.Status.ACTIVE).count(),
        'payments_month_rub': Payment.objects.filter(
            status=Payment.Status.PAID, paid_at__year=today.year, paid_at__month=today.month
        ).aggregate(s=Sum('amount_rub'))['s'] or 0,
        # Самые популярные сервисы среди всех пользователей
        'popular_services': Subscription.objects.values('name')
        .annotate(users=Count('user', distinct=True))
        .order_by('-users', 'name')[:6],
        'categories': Category.objects.annotate(subs=Count('subscriptions')).order_by('-subs'),
    }
    return render(request, 'management_panel/home.html', context)


# ---------------------------------------------------------------------------
# Пользователи
# ---------------------------------------------------------------------------

@admin_required
def user_list(request):
    users = User.objects.annotate(subs=Count('subscriptions')).order_by('email')
    query = request.GET.get('q', '').strip()
    if query:
        users = users.filter(Q(email__icontains=query) | Q(first_name__icontains=query) |
                             Q(last_name__icontains=query))
    return render(request, 'management_panel/user_list.html', {'users': users, 'query': query})


@admin_required
def user_update(request, pk):
    target = get_object_or_404(User, pk=pk)
    form = UserAdminForm(request.POST or None, instance=target)
    if request.method == 'POST' and form.is_valid():
        # Администратор не может лишить прав или заблокировать сам себя
        if target == request.user and (
            form.cleaned_data['role'] != User.Role.ADMIN or not form.cleaned_data['is_active']
        ):
            messages.error(request, 'Нельзя снять с себя роль администратора или заблокировать себя.')
        else:
            form.save()
            messages.success(request, f'Пользователь {target.email} обновлён.')
            return redirect('management_panel:users')
    return render(request, 'management_panel/user_form.html', {'form': form, 'target': target})


@admin_required
@require_POST
def user_toggle_active(request, pk):
    target = get_object_or_404(User, pk=pk)
    if target == request.user:
        messages.error(request, 'Нельзя заблокировать собственную учётную запись.')
    else:
        target.is_active = not target.is_active
        target.save(update_fields=['is_active'])
        state = 'разблокирован' if target.is_active else 'заблокирован'
        messages.success(request, f'Пользователь {target.email} {state}.')
    return redirect('management_panel:users')


# ---------------------------------------------------------------------------
# Справочники: категории и валюты (общий CRUD по словарю настроек)
# ---------------------------------------------------------------------------

REFERENCES = {
    'categories': {
        'model': Category, 'form': CategoryForm,
        'title': 'Категории сервисов', 'columns': ['name', 'description', 'color'],
        'headers': ['Название', 'Описание', 'Цвет'],
    },
    'currencies': {
        'model': Currency, 'form': CurrencyForm,
        'title': 'Валюты и курсы', 'columns': ['code', 'name', 'symbol', 'rate_to_rub'],
        'headers': ['Код', 'Название', 'Символ', 'Курс к ₽'],
    },
}


def get_reference(kind):
    config = REFERENCES.get(kind)
    if config is None:
        raise Http404('Справочник не найден')
    return config


@admin_required
def reference_list(request, kind):
    config = get_reference(kind)
    objects = config['model'].objects.all()
    rows = [(obj, [getattr(obj, col) for col in config['columns']]) for obj in objects]
    return render(request, 'management_panel/reference_list.html', {
        'kind': kind, 'config': config, 'rows': rows,
    })


@admin_required
def reference_edit(request, kind, pk=None):
    config = get_reference(kind)
    instance = get_object_or_404(config['model'], pk=pk) if pk else None
    form = config['form'](request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Запись сохранена.')
        return redirect('management_panel:reference_list', kind=kind)
    return render(request, 'management_panel/reference_form.html', {
        'kind': kind, 'config': config, 'form': form, 'instance': instance,
    })


@admin_required
@require_POST
def reference_delete(request, kind, pk):
    config = get_reference(kind)
    obj = get_object_or_404(config['model'], pk=pk)
    try:
        obj.delete()
        messages.success(request, 'Запись удалена.')
    except ProtectedError:
        # on_delete=PROTECT: нельзя удалить категорию/валюту, пока есть подписки
        messages.error(request, 'Нельзя удалить: запись используется в подписках пользователей.')
    return redirect('management_panel:reference_list', kind=kind)
