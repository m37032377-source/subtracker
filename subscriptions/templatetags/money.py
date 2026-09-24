"""Фильтр шаблонов для единообразного вывода денежных сумм: 12 345,60."""
from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def money(value, decimals=2):
    try:
        number = Decimal(value or 0)
    except (InvalidOperation, TypeError):
        return value
    text = f'{number:,.{int(decimals)}f}'           # 12,345.60
    # неразрывный пробел между разрядами и запятая перед копейками
    return text.replace(',', ' ').replace('.', ',')
