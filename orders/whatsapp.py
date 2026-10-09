"""Geração da mensagem e do link do WhatsApp.

O número NUNCA fica fixo no código: vem de StoreConfiguration.
O pedido é salvo no banco ANTES de qualquer abertura do WhatsApp.
"""

from urllib.parse import quote

from core.utils import format_brl

from .models import Order


def normalize_whatsapp_number(number: str) -> str:
    """Mantém apenas dígitos e adiciona o código do país (55) quando aplicável."""
    digits = "".join(ch for ch in (number or "") if ch.isdigit())
    if not digits:
        return ""
    if len(digits) in (10, 11):  # DDD + número (Brasil)
        digits = "55" + digits
    return digits


def build_message(order: Order, store_name: str = "") -> str:
    lines = [
        f"Olá{' ' + store_name if store_name else ''}! Gostaria de realizar um pedido.",
        "",
        f"*Pedido #{order.number}*",
        "",
        "*Produtos:*",
    ]
    for index, item in enumerate(order.items.all(), start=1):
        lines.append(f"{index}. {item.quantity}x {item.product_name} — {format_brl(item.subtotal)}")
    lines += [
        "",
        f"Subtotal: {format_brl(order.subtotal)}",
    ]
    if order.discount_total > 0:
        lines.append(f"Desconto: -{format_brl(order.discount_total)}")
    lines += [
        f"*TOTAL: {format_brl(order.total)}*",
        "",
        f"Forma de pagamento: {order.payment_method_name}",
        f"Nome: {order.customer_name}",
    ]
    if order.note:
        lines.append(f"Observação: {order.note}")
    return "\n".join(lines)


def build_whatsapp_url(order: Order, config) -> str | None:
    """URL wa.me pronta para abrir. Retorna None se o WhatsApp não estiver ativo/configurado."""
    if not getattr(config, "whatsapp_active", False):
        return None
    number = normalize_whatsapp_number(config.whatsapp_number)
    if not number:
        return None
    message = build_message(order, store_name=config.store_name)
    return f"https://wa.me/{number}?text={quote(message)}"
