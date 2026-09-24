"""Формы для работы с подписками и платежами."""
from django import forms

from .models import Category, Payment, Subscription


class BootstrapFormMixin:
    """Добавляет полям классы Bootstrap, чтобы не прописывать их в шаблонах."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput,)):
                widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault('class', 'form-select')
            else:
                widget.attrs.setdefault('class', 'form-control')


class SubscriptionForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Subscription
        fields = [
            'name', 'category', 'price', 'currency', 'billing_period', 'status',
            'start_date', 'next_payment_date', 'trial_end_date',
            'remind_days_before', 'website', 'notes',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'next_payment_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'trial_end_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        """Проверки, связывающие несколько полей между собой."""
        cleaned = super().clean()
        start = cleaned.get('start_date')
        next_payment = cleaned.get('next_payment_date')
        status = cleaned.get('status')
        trial_end = cleaned.get('trial_end_date')

        if start and next_payment and next_payment < start:
            self.add_error('next_payment_date', 'Дата списания не может быть раньше даты начала.')
        if status == Subscription.Status.TRIAL and not trial_end:
            self.add_error('trial_end_date', 'Для пробного периода укажите дату его окончания.')
        if trial_end and start and trial_end < start:
            self.add_error('trial_end_date', 'Пробный период не может закончиться раньше начала подписки.')
        return cleaned


class PaymentForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['subscription', 'amount', 'currency', 'paid_at', 'status', 'comment']
        widgets = {'paid_at': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Пользователь может выбрать только свои подписки
        if user is not None:
            self.fields['subscription'].queryset = user.subscriptions.order_by('name')


class SubscriptionFilterForm(BootstrapFormMixin, forms.Form):
    """Панель поиска и фильтрации на странице списка подписок."""

    SORT_CHOICES = [
        ('next_payment_date', 'По дате списания'),
        ('name', 'По названию'),
        ('-price', 'Сначала дорогие'),
        ('price', 'Сначала дешёвые'),
    ]

    q = forms.CharField(label='Поиск', required=False,
                        widget=forms.TextInput(attrs={'placeholder': 'Название сервиса'}))
    category = forms.ModelChoiceField(label='Категория', queryset=Category.objects.all(),
                                      required=False, empty_label='Все категории')
    status = forms.ChoiceField(label='Статус', required=False,
                               choices=[('', 'Все статусы')] + list(Subscription.Status.choices))
    period = forms.ChoiceField(label='Период', required=False,
                               choices=[('', 'Любой период')] + list(Subscription.BillingPeriod.choices))
    sort = forms.ChoiceField(label='Сортировка', required=False, choices=SORT_CHOICES)
