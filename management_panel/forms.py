from django import forms

from accounts.models import User
from subscriptions.forms import BootstrapFormMixin
from subscriptions.models import Category, Currency


class CategoryForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'icon', 'color']
        widgets = {'color': forms.TextInput(attrs={'type': 'color'})}


class CurrencyForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Currency
        fields = ['code', 'name', 'symbol', 'rate_to_rub']

    def clean_code(self):
        return self.cleaned_data['code'].upper()


class UserAdminForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'role', 'is_active', 'monthly_budget']
