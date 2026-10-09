from django.db import models


class Customer(models.Model):
    """Cliente identificado apenas por telefone (sem necessidade de conta)."""

    name = models.CharField("Nome", max_length=120)
    phone = models.CharField("Telefone/WhatsApp", max_length=30, unique=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def __str__(self):
        return f"{self.name} ({self.phone})"
