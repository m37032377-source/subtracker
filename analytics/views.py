"""Страница аналитики расходов и выгрузка отчётов в CSV и Excel."""
import csv
from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from subscriptions.models import Category

from . import services


def get_period(request) -> services.Period:
    """Читает период из GET-параметров ?from=ГГГГ-ММ-ДД&to=ГГГГ-ММ-ДД.
    Некорректные или перепутанные даты заменяются значениями по умолчанию."""
    today = timezone.localdate()
    period = services.default_period(today)
    try:
        if request.GET.get('from'):
            period.date_from = date.fromisoformat(request.GET['from'])
        if request.GET.get('to'):
            period.date_to = date.fromisoformat(request.GET['to'])
    except ValueError:
        return services.default_period(today)
    if period.date_from > period.date_to:
        period.date_from, period.date_to = period.date_to, period.date_from
    return period


@login_required
def analytics_dashboard(request):
    period = get_period(request)
    user = request.user
    months = services.by_month(user, period)
    categories = services.by_category(user, period)

    # Данные для Chart.js передаются в шаблон и выводятся через json_script
    chart_data = {
        'months': {
            'labels': [m['month'] for m in months],
            'values': [float(m['total']) for m in months],
        },
        'categories': {
            'labels': [c['name'] for c in categories],
            'values': [float(c['total']) for c in categories],
            'colors': [c['color'] for c in categories],
        },
    }
    return render(request, 'analytics/dashboard.html', {
        'period': period,
        'summary': services.summary(user, period),
        'categories': categories,
        'top': services.top_subscriptions(user, period),
        'planned': services.planned_by_category(user),
        'chart_data': chart_data,
        'all_categories': Category.objects.count(),
    })


EXPORT_HEADERS = ['Дата', 'Подписка', 'Категория', 'Сумма', 'Валюта', 'Сумма, ₽', 'Статус', 'Комментарий']


def export_rows(user, period):
    payments = services.paid_payments(user, period).select_related(
        'subscription', 'subscription__category', 'currency'
    ).order_by('paid_at')
    for p in payments:
        yield [
            p.paid_at.strftime('%d.%m.%Y'), p.subscription.name, p.subscription.category.name,
            p.amount, p.currency.code, p.amount_rub, p.get_status_display(), p.comment,
        ]


@login_required
def export_csv(request):
    period = get_period(request)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = (
        f'attachment; filename="expenses_{period.date_from}_{period.date_to}.csv"'
    )
    response.write('﻿')  # BOM, чтобы Excel правильно открыл кириллицу
    writer = csv.writer(response, delimiter=';')
    writer.writerow(EXPORT_HEADERS)
    for row in export_rows(request.user, period):
        writer.writerow(row)
    return response


@login_required
def export_xlsx(request):
    period = get_period(request)
    workbook = Workbook()

    # Лист 1 — все платежи за период
    sheet = workbook.active
    sheet.title = 'Платежи'
    sheet.append(EXPORT_HEADERS)
    for row in export_rows(request.user, period):
        sheet.append([float(v) if hasattr(v, 'quantize') else v for v in row])

    # Лист 2 — итоги по категориям
    summary_sheet = workbook.create_sheet('По категориям')
    summary_sheet.append(['Категория', 'Сумма'])
    for item in services.by_category(request.user, period):
        summary_sheet.append([item['name'], float(item['total'])])

    header_fill = PatternFill('solid', fgColor='4F46E5')
    for ws in workbook.worksheets:
        for cell in ws[1]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = header_fill
        for column in ws.columns:
            width = max(len(str(c.value or '')) for c in column) + 2
            ws.column_dimensions[column[0].column_letter].width = min(width, 45)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = (
        f'attachment; filename="expenses_{period.date_from}_{period.date_to}.xlsx"'
    )
    workbook.save(response)
    return response
