"""Декораторы для разграничения прав доступа по ролям."""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect


def admin_required(view_func):
    """Пропускает к представлению только администратора.

    1. Гость перенаправляется на страницу входа.
    2. Обычный пользователь получает сообщение об ошибке и возвращается на главную.
    3. Администратор получает доступ к исходной функции view_func.
    """

    @wraps(view_func)  # сохраняет имя и описание исходной функции
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.is_admin:
            messages.error(request, 'Раздел доступен только администратору.')
            return redirect('subscriptions:dashboard')
        return view_func(request, *args, **kwargs)

    return wrapper
