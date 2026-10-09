from django import forms
from django.core.validators import RegexValidator

from .models import PaymentMethod

phone_validator = RegexValidator(
    regex=r"^\(?\d{2}\)?\s?9?\d{4}-?\d{4}$",
    message="Informe um telefone válido com DDD, ex.: (11) 98765-4321.",
)


class CheckoutForm(forms.Form):
    customer_name = forms.CharField(
        label="Nome completo",
        max_length=120,
        widget=forms.TextInput(attrs={"class": "input", "autocomplete": "name", "required": True}),
    )
    customer_phone = forms.CharField(
        label="Telefone / WhatsApp",
        max_length=30,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={"class": "input", "autocomplete": "tel", "inputmode": "tel", "required": True}),
    )
    note = forms.CharField(
        label="Observação",
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={"class": "input", "rows": 3}),
    )
    payment_method = forms.ModelChoiceField(
        label="Forma de pagamento", queryset=PaymentMethod.objects.none(), empty_label=None
    )
    idempotency_key = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["payment_method"].queryset = PaymentMethod.objects.filter(is_active=True).order_by(
            "order", "id"
        )

    def clean_customer_name(self):
        name = self.cleaned_data["customer_name"].strip()
        if len(name) < 3:
            raise forms.ValidationError("Informe seu nome completo.")
        return name
