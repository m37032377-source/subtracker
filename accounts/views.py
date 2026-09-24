"""Регистрация, вход, выход и профиль пользователя."""
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render

from subscriptions.services import monthly_total

from .forms import LoginForm, ProfileForm, RegisterForm


class UserLoginView(LoginView):
    """Стандартное представление входа Django с нашей формой и шаблоном."""

    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True  # уже вошедшего пользователя сразу отправляем на главную


class UserLogoutView(LogoutView):
    next_page = 'accounts:login'


def register(request):
    if request.user.is_authenticated:
        return redirect('subscriptions:dashboard')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)  # сразу авторизуем после регистрации
        messages.success(request, 'Добро пожаловать! Добавьте первую подписку.')
        return redirect('subscriptions:dashboard')
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile(request):
    profile_form = ProfileForm(request.POST or None, instance=request.user, prefix='profile')
    password_form = PasswordChangeForm(request.user, request.POST or None, prefix='password')
    for field in password_form.fields.values():
        field.widget.attrs['class'] = 'form-control'

    if request.method == 'POST':
        if 'save_profile' in request.POST and profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Профиль обновлён.')
            return redirect('accounts:profile')
        if 'change_password' in request.POST and password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)  # чтобы не разлогинило после смены пароля
            messages.success(request, 'Пароль изменён.')
            return redirect('accounts:profile')

    return render(request, 'accounts/profile.html', {
        'profile_form': profile_form,
        'password_form': password_form,
        'month_total': monthly_total(request.user),
        'subscriptions_count': request.user.subscriptions.count(),
    })
