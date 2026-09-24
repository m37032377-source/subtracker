"""Модель пользователя и ролевая модель приложения."""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Менеджер пользователей: вход выполняется по email, а не по username."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Email обязателен')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # пароль хранится только в виде хеша
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', User.Role.USER)
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', User.Role.ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Пользователь системы.

    Наследуется от стандартного AbstractUser (пароль, is_active, даты входа),
    но вместо username для входа используется email. Добавлены роль,
    основная валюта и месячный бюджет на подписки.
    """

    class Role(models.TextChoices):
        USER = 'user', 'Пользователь'
        ADMIN = 'admin', 'Администратор'

    username = None
    email = models.EmailField('Email', unique=True)
    role = models.CharField('Роль', max_length=10, choices=Role.choices, default=Role.USER)
    default_currency = models.ForeignKey(
        'subscriptions.Currency',
        verbose_name='Основная валюта',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
    )
    monthly_budget = models.DecimalField(
        'Месячный бюджет на подписки', max_digits=10, decimal_places=2, null=True, blank=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['email']

    def save(self, *args, **kwargs):
        # Роль администратора синхронизируется с доступом к стандартной админке Django
        if self.role == self.Role.ADMIN:
            self.is_staff = True
        super().save(*args, **kwargs)

    @property
    def is_admin(self) -> bool:
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def display_name(self) -> str:
        return self.get_full_name() or self.email

    def __str__(self):
        return self.display_name
