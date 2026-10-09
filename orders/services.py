"""Operações críticas de estoque e criação de pedidos.

Todas as operações que alteram estoque ou criam pedidos rodam dentro de
transações atômicas com bloqueio de linha (select_for_update), impedindo
estoque negativo em cenários de concorrência.
"""

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
import logging

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from core.models import AuditLog, StoreConfiguration
from core.utils import money

from .models import Order, OrderItem, StockReservation

logger = logging.getLogger("orders")


class OrderError(Exception):
    """Erro seguro para exibição ao usuário final (sem detalhes técnicos)."""


@dataclass
class CartLineData:
    """Linha do carrinho já normalizada para processamento no backend."""

    product_id: int
    quantity: int


def release_expired_reservations() -> int:
    """Libera reservas vencidas. Retorna a quantidade liberada."""
    now = timezone.now()
    expired = StockReservation.objects.filter(status=StockReservation.Status.ACTIVE, expires_at__lt=now)
    count = expired.update(status=StockReservation.Status.RELEASED)
    if count:
        logger.info("Reservas expiradas liberadas: %s", count)
    return count


def get_reserved_map(exclude_session: str | None = None) -> dict[int, int]:
    """Mapa {product_id: quantidade} de reservas ativas (não expiradas).

    exclude_session ignora as reservas da própria sessão (para exibir
    disponibilidade correta na página do produto).
    """
    now = timezone.now()
    qs = StockReservation.objects.filter(status=StockReservation.Status.ACTIVE, expires_at__gte=now)
    if exclude_session:
        qs = qs.exclude(session_key=exclude_session)
    rows = qs.values("product_id").annotate(total=Sum("quantity"))
    return {row["product_id"]: row["total"] for row in rows}


def reserve_for_session(session_key: str, lines: list[CartLineData]) -> None:
    """(Re)cria as reservas temporárias da sessão durante o checkout."""
    config = StoreConfiguration.load()
    minutes = config.reservation_minutes or getattr(settings, "RESERVATION_MINUTES_DEFAULT", 15)
    expires_at = timezone.now() + timedelta(minutes=minutes)
    with transaction.atomic():
        StockReservation.objects.filter(
            session_key=session_key, status=StockReservation.Status.ACTIVE
        ).update(status=StockReservation.Status.RELEASED)
        product_ids = [line.product_id for line in lines]
        products = {p.pk: p for p in _locked_products(product_ids)}
        reserved_others = get_reserved_map()
        for line in lines:
            product = products.get(line.product_id)
            if product is None or not product.is_active:
                raise OrderError("Um dos produtos não está mais disponível. Atualize o carrinho.")
            if product.stock - reserved_others.get(product.pk, 0) < line.quantity and not (
                product.allow_backorder or config.allow_order_when_zero_stock
            ):
                raise OrderError(
                    f"Não há estoque suficiente de {product.name} no momento. Tente novamente em instantes."
                )
            StockReservation.objects.create(
                product=product,
                session_key=session_key,
                quantity=line.quantity,
                status=StockReservation.Status.ACTIVE,
                expires_at=expires_at,
            )


def _locked_products(product_ids: list[int]):
    from catalog.models import Product

    return Product.objects.select_for_update().filter(pk__in=product_ids).order_by("pk")


@transaction.atomic
def create_order(
    *,
    lines: list[CartLineData],
    customer_name: str,
    customer_phone: str,
    note: str,
    payment_method,
    idempotency_key: str,
    session_key: str = "",
    user=None,
) -> Order:
    """Cria o pedido de forma transacional, recalculando TODOS os valores no servidor.

    Garante: preços do banco, desconto recalculado, estoque não-negativo,
    snapshot do pedido, número único e idempotência.
    """
    from catalog.models import Product
    from customers.models import Customer

    if not lines:
        raise OrderError("Seu carrinho está vazio.")

    existing = Order.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing

    config = StoreConfiguration.load()
    reserved_others = get_reserved_map(exclude_session=session_key or None)
    products = {p.pk: p for p in _locked_products([line.product_id for line in lines])}

    subtotal = Decimal("0")
    discount_total = Decimal("0")
    items_data = []

    for line in lines:
        product = products.get(line.product_id)
        if product is None or not product.is_active:
            raise OrderError("Um dos produtos não está mais disponível. Atualize o carrinho.")

        quantity = line.quantity
        others = reserved_others.get(product.pk, 0)
        available = product.stock - others

        backorder = available < quantity and (
            product.allow_backorder or config.allow_order_when_zero_stock
        )
        if available < quantity and not backorder:
            raise OrderError(
                f"O estoque de {product.name} acabou de esgotar. Remova o item ou reduza a quantidade."
            )

        # Preços SEMPRE vindos do banco (nunca confiados ao navegador).
        unit_price = money(product.price)
        unit_discount = money(product.discount_amount)
        unit_final = money(product.final_price)
        line_subtotal = money(unit_final * quantity)

        subtotal += unit_price * quantity
        discount_total += unit_discount * quantity
        items_data.append((product, quantity, unit_price, unit_discount, unit_final, line_subtotal))

        if not backorder:
            product.stock = product.stock - quantity
            if product.stock < 0:  # proteção extra contra estoque negativo
                raise OrderError(
                    f"O estoque de {product.name} acabou de esgotar. Tente novamente."
                )
            product.save(update_fields=["stock", "updated_at"])

    subtotal = money(subtotal)
    discount_total = money(discount_total)
    total = money(subtotal - discount_total)

    order = Order(
        customer_name=customer_name.strip(),
        customer_phone=customer_phone.strip(),
        note=note.strip(),
        payment_method=payment_method,
        payment_method_name=payment_method.name if payment_method else "",
        subtotal=subtotal,
        discount_total=discount_total,
        total=total,
        idempotency_key=idempotency_key,
    )
    order.save()

    for product, quantity, unit_price, unit_discount, unit_final, line_subtotal in items_data:
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            unit_price=unit_price,
            discount_value=unit_discount,
            unit_final_price=unit_final,
            quantity=quantity,
            subtotal=line_subtotal,
        )

    # Converte as reservas da sessão em reservas do pedido.
    if session_key:
        StockReservation.objects.filter(
            session_key=session_key, status=StockReservation.Status.ACTIVE
        ).update(status=StockReservation.Status.CONVERTED, order=order)

    Customer.objects.update_or_create(
        phone=customer_phone.strip(),
        defaults={"name": customer_name.strip()},
    )

    AuditLog.log(
        "Pedido criado",
        order,
        user,
        f"Cliente: {order.customer_name} | Total: R$ {order.total} | Pagamento: {order.payment_method_name}",
    )
    logger.info("Pedido %s criado. Total: R$ %s", order.number, order.total)
    return order


def cancel_order(order: Order, user=None, reason: str = "") -> None:
    """Cancela o pedido e devolve o estoque dos itens que o baixaram."""
    from catalog.models import Product

    with transaction.atomic():
        if order.status == Order.Status.CANCELLED:
            raise OrderError("Este pedido já está cancelado.")
        order.cancel(user=user, reason=reason)
        for item in order.items.select_related("product"):
            if item.product is not None and item.product.is_active:
                Product.objects.filter(pk=item.product.pk).update(
                    stock=item.product.stock + item.quantity
                )
                item.product.refresh_from_db(fields=["stock"])
        AuditLog.log("Pedido cancelado", order, user, reason)
        logger.info("Pedido %s cancelado por %s", order.number, user)
