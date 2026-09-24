"""Формы регистрации, входа и редактирования профиля."""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from subscriptions.forms import BootstrapFormMixin

from .models import User


class RegisterForm(BootstrapFormMixin, UserCreationForm):
    """Регистрация нового пользователя.

    UserCreationForm уже проверяет совпадение паролей и прогоняет пароль через
    валидаторы из AUTH_PASSWORD_VALIDATORS. Роль всегда «Пользователь» —
    назначить администратора может только другой администратор.
    """

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'default_currency')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.USER
        if commit:
            user.save()
        return user


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    username = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'autofocus': True}))


class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'default_currency', 'monthly_budget')
