"""Carrinho baseado em sessão.

O carrinho guarda APENAS pares (product_id, quantidade) na sessão.
Todos os preços, descontos e totais são recalculados no servidor a partir
do banco — nunca confiados ao navegador.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from core.models import StoreConfiguration
from core.utils import money
from orders.services import OrderError, get_reserved_map as _get_reserved_map

from catalog.models import Product


@dataclass
class CartLine:
    product: Product
    quantity: int
    unit_price: Decimal
    unit_discount: Decimal
    unit_final_price: Decimal
    subtotal: Decimal


@dataclass
class Cart:
    lines: list = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.lines

    @property
    def subtotal(self) -> Decimal:
        return money(sum((line.unit_price * line.quantity for line in self.lines), Decimal("0")))

    @property
    def discount_total(self) -> Decimal:
        return money(sum((line.unit_discount * line.quantity for line in self.lines), Decimal("0")))

    @property
    def total(self) -> Decimal:
        return money(sum((line.subtotal for line in self.lines), Decimal("0")))

    @property
    def item_count(self) -> int:
        return sum(line.quantity for line in self.lines)


def get_reserved_map(exclude_session=None):
    return _get_reserved_map(exclude_session=exclude_session)


def load_cart(request) -> Cart:
    """Reconstrói o carrinho a partir da sessão, sempre recalculando no servidor."""
    cart = Cart()
    raw = request.session.get("beauty_cart", {})
    if not raw:
        return cart

    session_key = request.session.session_key or ""
    reserved_others = get_reserved_map(exclude_session=session_key)

    products = Product.objects.filter(pk__in=raw.keys(), is_active=True).prefetch_related("images")
    for product in products:
        try:
            quantity = max(1, min(int(raw[str(product.pk)]), 99))
        except (KeyError, TypeError, ValueError):
            continue
        max_available = product.stock - reserved_others.get(product.pk, 0)
        config = StoreConfiguration.load()
        can_backorder = product.allow_backorder or config.allow_order_when_zero_stock
        if max_available <= 0 and not can_backorder:
            continue  # produto esgotado: não entra no carrinho
        if max_available > 0:
            quantity = min(quantity, max_available)
        cart.lines.append(
            CartLine(
                product=product,
                quantity=quantity,
                unit_price=money(product.price),
                unit_discount=money(product.discount_amount),
                unit_final_price=money(product.final_price),
                subtotal=money(product.final_price * quantity),
            )
        )
    cart.lines.sort(key=lambda line: line.product.name)
    return cart


def save_cart(request, cart_data: dict) -> None:
    request.session["beauty_cart"] = {str(k): int(v) for k, v in cart_data.items() if int(v) > 0}


def clear_cart(request) -> None:
    request.session.pop("beauty_cart", None)


def add_to_cart(request, product_id: int, quantity: int = 1) -> None:
    product = Product.objects.filter(pk=product_id, is_active=True).first()
    if product is None:
        raise OrderError("Produto não disponível.")
    raw = request.session.get("beauty_cart", {})
    current = int(raw.get(str(product_id), 0))
    new_quantity = current + max(1, quantity)

    config = StoreConfiguration.load()
    reserved_others = get_reserved_map(exclude_session=request.session.session_key)
    max_available = product.stock - reserved_others.get(product.pk, 0)
    can_backorder = product.allow_backorder or config.allow_order_when_zero_stock

    if max_available <= 0 and not can_backorder:
        raise OrderError(f"{product.name} está sem estoque no momento.")
    limit = max_available if max_available > 0 else 99
    if new_quantity > limit:
        raise OrderError(f"Estoque disponível de {product.name}: {limit} unidade(s).")

    raw[str(product_id)] = new_quantity
    save_cart(request, raw)


def update_quantity(request, product_id: int, quantity: int) -> None:
    raw = request.session.get("beauty_cart", {})
    if str(product_id) not in raw:
        raise OrderError("Item não encontrado no carrinho.")
    if quantity <= 0:
        raw.pop(str(product_id), None)
        save_cart(request, raw)
        return
    product = Product.objects.filter(pk=product_id, is_active=True).first()
    if product is None:
        raw.pop(str(product_id), None)
        save_cart(request, raw)
        raise OrderError("Produto não disponível.")
    config = StoreConfiguration.load()
    reserved_others = get_reserved_map(exclude_session=request.session.session_key)
    max_available = product.stock - reserved_others.get(product.pk, 0)
    can_backorder = product.allow_backorder or config.allow_order_when_zero_stock
    if max_available <= 0 and not can_backorder:
        raw.pop(str(product_id), None)
        save_cart(request, raw)
        raise OrderError(f"{product.name} está sem estoque no momento.")
    quantity = min(max(1, quantity), max_available if max_available > 0 else 99)
    raw[str(product_id)] = quantity
    save_cart(request, raw)


def remove_from_cart(request, product_id: int) -> None:
    raw = request.session.get("beauty_cart", {})
    raw.pop(str(product_id), None)
    save_cart(request, raw)
