from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from core.models import AuditLog


class PaymentMethod(models.Model):
    name = models.CharField("Nome", max_length=60)
    instructions = models.TextField("Instruções", blank=True, default="")
    order = models.PositiveIntegerField("Ordem", default=0)
    is_active = models.BooleanField("Ativa", default=True)

    class Meta:
        ordering = ("order", "id")
        verbose_name = "Forma de pagamento"
        verbose_name_plural = "Formas de pagamento"

    def __str__(self):
        return self.name


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = "novo", "Novo"
        AWAITING_CONTACT = "aguardando_contato", "Aguardando contato"
        IN_ATTENDANCE = "em_atendimento", "Em atendimento"
        AWAITING_PAYMENT = "aguardando_pagamento", "Aguardando pagamento"
        PAID = "pago", "Pago"
        PREPARING = "preparando", "Preparando"
        READY = "pronto", "Pronto"
        DELIVERED = "entregue", "Entregue"
        CANCELLED = "cancelado", "Cancelado"
        EXPIRED = "expirado", "Expirado"

    # Transições permitidas a partir de cada status.
    TRANSITIONS = {
        Status.NEW: {
            Status.AWAITING_CONTACT, Status.IN_ATTENDANCE, Status.AWAITING_PAYMENT,
            Status.PAID, Status.PREPARING, Status.READY, Status.DELIVERED,
            Status.CANCELLED, Status.EXPIRED,
        },
        Status.AWAITING_CONTACT: {Status.IN_ATTENDANCE, Status.AWAITING_PAYMENT, Status.PAID, Status.CANCELLED, Status.EXPIRED},
        Status.IN_ATTENDANCE: {Status.AWAITING_PAYMENT, Status.PAID, Status.PREPARING, Status.CANCELLED, Status.EXPIRED},
        Status.AWAITING_PAYMENT: {Status.PAID, Status.IN_ATTENDANCE, Status.CANCELLED, Status.EXPIRED},
        Status.PAID: {Status.PREPARING, Status.READY, Status.DELIVERED, Status.CANCELLED},
        Status.PREPARING: {Status.READY, Status.DELIVERED, Status.CANCELLED},
        Status.READY: {Status.DELIVERED, Status.CANCELLED},
        Status.DELIVERED: set(),
        Status.CANCELLED: set(),
        Status.EXPIRED: set(),
    }

    number = models.CharField("Número", max_length=24, unique=True, blank=True)
    idempotency_key = models.CharField("Chave de idempotência", max_length=64, unique=True, null=True, blank=True)

    customer_name = models.CharField("Nome do cliente", max_length=120)
    customer_phone = models.CharField("Telefone/WhatsApp", max_length=30)
    note = models.TextField("Observação", blank=True, default="")

    payment_method = models.ForeignKey(
        PaymentMethod, verbose_name="Forma de pagamento", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="orders",
    )
    payment_method_name = models.CharField("Forma de pagamento (registro)", max_length=60, blank=True, default="")

    subtotal = models.DecimalField("Subtotal", max_digits=12, decimal_places=2, default=Decimal("0"))
    discount_total = models.DecimalField("Desconto", max_digits=12, decimal_places=2, default=Decimal("0"))
    total = models.DecimalField("Total", max_digits=12, decimal_places=2, default=Decimal("0"))

    status = models.CharField("Status", max_length=30, choices=Status.choices, default=Status.NEW)

    created_at = models.DateTimeField("Criado em", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)
    cancelled_at = models.DateTimeField("Cancelado em", null=True, blank=True)
    cancellation_reason = models.TextField("Motivo do cancelamento", blank=True, default="")
    cancelled_by = models.ForeignKey(
        "auth.User", verbose_name="Cancelado por", null=True, blank=True, on_delete=models.SET_NULL, related_name="cancelled_orders"
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self):
        return f"{self.number or '(sem número)'} — {self.customer_name}"

    def save(self, *args, **kwargs):
        if not self.number:
            # Número gerado a partir do pk (único e sequencial por ano de criação).
            super().save(*args, **kwargs)
            self.number = f"PED-{self.created_at.year}-{self.pk:06d}"
            super().save(update_fields=["number"])
            return
        super().save(*args, **kwargs)

    def transition_to(self, new_status: str, user=None, reason: str = ""):
        """Aplica uma transição de status válida e registra auditoria."""
        new_status = self.Status(new_status)
        allowed = self.TRANSITIONS.get(self.Status(self.status), set())
        if new_status not in allowed:
            raise ValueError(f"Transição inválida: {self.get_status_display()} -> {new_status.label}")
        old = self.get_status_display()
        self.status = new_status
        if new_status == self.Status.CANCELLED:
            from django.utils import timezone

            self.cancelled_at = timezone.now()
            self.cancellation_reason = reason
            self.cancelled_by = user if getattr(user, "is_authenticated", False) else None
        self.save(update_fields=["status", "cancelled_at", "cancellation_reason", "cancelled_by", "updated_at"])
        AuditLog.log(
            f"Status do pedido alterado: {old} -> {new_status.label}",
            self,
            user,
            reason,
        )

    def cancel(self, user=None, reason: str = ""):
        """Cancelamento lógico: nunca excluir pedidos."""
        self.transition_to(self.Status.CANCELLED, user=user, reason=reason)


class OrderItem(models.Model):
    """Snapshot do item no momento da compra: nunca recalculado depois."""

    order = models.ForeignKey(Order, verbose_name="Pedido", on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "catalog.Product", verbose_name="Produto", null=True, blank=True, on_delete=models.SET_NULL, related_name="order_items"
    )
    product_name = models.CharField("Nome do produto", max_length=200)
    unit_price = models.DecimalField("Preço unitário (tabela)", max_digits=10, decimal_places=2)
    discount_value = models.DecimalField("Desconto unitário", max_digits=10, decimal_places=2, default=Decimal("0"))
    unit_final_price = models.DecimalField("Preço unitário final", max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField("Quantidade", validators=[MinValueValidator(1)])
    subtotal = models.DecimalField("Subtotal", max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "Item do pedido"
        verbose_name_plural = "Itens do pedido"

    def __str__(self):
        return f"{self.quantity}x {self.product_name}"


class StockReservation(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativa"
        CONVERTED = "converted", "Convertida (pedido confirmado)"
        RELEASED = "released", "Liberada"

    product = models.ForeignKey("catalog.Product", verbose_name="Produto", on_delete=models.CASCADE, related_name="reservations")
    order = models.ForeignKey(
        Order, verbose_name="Pedido", null=True, blank=True, on_delete=models.SET_NULL, related_name="reservations"
    )
    session_key = models.CharField("Sessão", max_length=64, blank=True, default="")
    quantity = models.PositiveIntegerField("Quantidade")
    status = models.CharField("Status", max_length=12, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField("Criada em", auto_now_add=True)
    expires_at = models.DateTimeField("Expira em", db_index=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Reserva de estoque"
        verbose_name_plural = "Reservas de estoque"
        indexes = [models.Index(fields=["status", "expires_at"])]

    def __str__(self):
        return f"{self.quantity}x {self.product} ({self.get_status_display()})"
