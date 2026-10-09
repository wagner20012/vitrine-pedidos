from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.test import TestCase
from django.utils import timezone

from catalog.models import Category, Product
from core.models import StoreConfiguration
from orders.models import Order, OrderItem, PaymentMethod, StockReservation
from orders.services import (
    CartLineData,
    OrderError,
    create_order,
    get_reserved_map,
    release_expired_reservations,
    reserve_for_session,
)
from orders.whatsapp import build_message, build_whatsapp_url, normalize_whatsapp_number


class OrderServiceBase(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Perfumes")
        self.payment = PaymentMethod.objects.create(name="Pix")
        self.product = Product.objects.create(
            name="Perfume Floral",
            category=self.category,
            price=Decimal("100.00"),
            stock=10,
        )
        self.discounted = Product.objects.create(
            name="Batom Nude",
            category=self.category,
            price=Decimal("50.00"),
            stock=5,
            discount_type=Product.DiscountType.PERCENT,
            discount_value=Decimal("10"),
        )


class CreateOrderTests(OrderServiceBase):
    def _create(self, idempotency_key="key-1", session="sess-1"):
        return create_order(
            lines=[
                CartLineData(product_id=self.product.pk, quantity=1),
                CartLineData(product_id=self.discounted.pk, quantity=2),
            ],
            customer_name="João da Silva",
            customer_phone="11987654321",
            note="Entregar à tarde",
            payment_method=self.payment,
            idempotency_key=idempotency_key,
            session_key=session,
        )

    def test_criacao_e_valores(self):
        order = self._create()
        self.assertTrue(order.number.startswith("PED-"))
        self.assertEqual(order.subtotal, Decimal("200.00"))
        self.assertEqual(order.discount_total, Decimal("10.00"))
        self.assertEqual(order.total, Decimal("190.00"))
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.status, Order.Status.NEW)

    def test_snapshot_de_precos(self):
        """Alterar preço depois NUNCA muda o pedido antigo."""
        order = self._create()
        self.product.price = Decimal("150.00")
        self.product.save()
        self.discounted.discount_value = Decimal("20")
        self.discounted.save()
        order.refresh_from_db()
        item = order.items.get(product=self.product)
        self.assertEqual(item.unit_price, Decimal("100.00"))
        item2 = order.items.get(product=self.discounted)
        self.assertEqual(item2.unit_final_price, Decimal("45.00"))
        self.assertEqual(order.total, Decimal("190.00"))

    def test_estoque_e_baixado(self):
        self._create()
        self.product.refresh_from_db()
        self.discounted.refresh_from_db()
        self.assertEqual(self.product.stock, 9)
        self.assertEqual(self.discounted.stock, 3)

    def test_estoque_nao_negativo(self):
        with self.assertRaises(OrderError):
            create_order(
                lines=[CartLineData(product_id=self.product.pk, quantity=11)],
                customer_name="Cliente",
                customer_phone="11987654321",
                note="",
                payment_method=self.payment,
                idempotency_key="key-2",
            )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)
        self.assertFalse(Order.objects.exists())

    def test_produto_inativo_rejeitado(self):
        self.product.is_active = False
        self.product.save()
        with self.assertRaises(OrderError):
            self._create()

    def test_idempotencia(self):
        order1 = self._create(idempotency_key="abc")
        # Mesma chave: retorna o mesmo pedido, sem duplicar nem baixar estoque de novo.
        order2 = create_order(
            lines=[CartLineData(product_id=self.product.pk, quantity=1)],
            customer_name="João da Silva",
            customer_phone="11987654321",
            note="",
            payment_method=self.payment,
            idempotency_key="abc",
        )
        self.assertEqual(order1.pk, order2.pk)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 9)

    def test_backorder_permite_estoque_zero(self):
        self.product.stock = 0
        self.product.allow_backorder = True
        self.product.save()
        order = create_order(
            lines=[CartLineData(product_id=self.product.pk, quantity=2)],
            customer_name="Cliente",
            customer_phone="11987654321",
            note="",
            payment_method=self.payment,
            idempotency_key="key-bo",
        )
        self.assertEqual(order.items.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)  # encomenda não baixa estoque

    def test_configuracao_global_de_encomenda(self):
        config = StoreConfiguration.load()
        config.allow_order_when_zero_stock = True
        config.save()
        self.discounted.stock = 0
        self.discounted.allow_backorder = False
        self.discounted.save()
        order = create_order(
            lines=[CartLineData(product_id=self.discounted.pk, quantity=1)],
            customer_name="Cliente",
            customer_phone="11987654321",
            note="",
            payment_method=self.payment,
            idempotency_key="key-cfg",
        )
        self.assertEqual(order.total, Decimal("45.00"))

    def test_cancelamento_devolve_estoque(self):
        from orders.services import cancel_order

        order = self._create()
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 9)
        cancel_order(order, user=None, reason="Cliente desistiu")
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertTrue(order.cancelled_at)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)
        self.discounted.refresh_from_db()
        self.assertEqual(self.discounted.stock, 5)

    def test_pedido_nao_pode_ser_excluido_apos_cancelado(self):
        """Cancelamento é lógico: o histórico permanece."""
        from orders.services import cancel_order

        order = self._create()
        cancel_order(order, reason="teste")
        order.refresh_from_db()
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.cancellation_reason, "teste")


class ReservationTests(OrderServiceBase):
    def test_reserva_e_conversao(self):
        reserve_for_session("sess-a", [CartLineData(product_id=self.product.pk, quantity=2)])
        reserved = get_reserved_map()
        self.assertEqual(reserved.get(self.product.pk), 2)
        # Outras sessões veem a reserva
        self.assertEqual(get_reserved_map(exclude_session="sess-b").get(self.product.pk), 2)
        # A própria sessão não se bloqueia
        self.assertIsNone(get_reserved_map(exclude_session="sess-a").get(self.product.pk))

        order = create_order(
            lines=[CartLineData(product_id=self.product.pk, quantity=2)],
            customer_name="Cliente",
            customer_phone="11987654321",
            note="",
            payment_method=self.payment,
            idempotency_key="key-r1",
            session_key="sess-a",
        )
        reservation = StockReservation.objects.get(session_key="sess-a")
        self.assertEqual(reservation.status, StockReservation.Status.CONVERTED)
        self.assertEqual(reservation.order, order)

    def test_expiracao_libera_estoque(self):
        reserve_for_session("sess-a", [CartLineData(product_id=self.product.pk, quantity=3)])
        # Força expiração no passado
        StockReservation.objects.update(expires_at=timezone.now() - timedelta(minutes=1))
        count = release_expired_reservations()
        self.assertEqual(count, 1)
        self.assertEqual(get_reserved_map().get(self.product.pk), None)

    def test_reserva_insuficiente_rejeita(self):
        reserve_for_session("sess-a", [CartLineData(product_id=self.product.pk, quantity=8)])
        with self.assertRaises(OrderError):
            reserve_for_session("sess-b", [CartLineData(product_id=self.product.pk, quantity=3)])


class WhatsAppTests(OrderServiceBase):
    def _order(self):
        return create_order(
            lines=[
                CartLineData(product_id=self.product.pk, quantity=1),
                CartLineData(product_id=self.discounted.pk, quantity=2),
            ],
            customer_name="João",
            customer_phone="11987654321",
            note="Entregar à tarde.",
            payment_method=self.payment,
            idempotency_key="wa-1",
        )

    def test_numero_normalizado(self):
        self.assertEqual(normalize_whatsapp_number("11987654321"), "5511987654321")
        self.assertEqual(normalize_whatsapp_number("(11) 98765-4321"), "5511987654321")
        self.assertEqual(normalize_whatsapp_number("5511987654321"), "5511987654321")
        self.assertEqual(normalize_whatsapp_number(""), "")

    def test_mensagem_contem_pedido_e_valores(self):
        config = StoreConfiguration.load()
        config.whatsapp_number = "11999990000"
        config.whatsapp_active = True
        config.save()
        order = self._order()
        url = build_whatsapp_url(order, config)
        self.assertTrue(url.startswith("https://wa.me/5511999990000?text="))
        message = build_message(order, store_name=config.store_name)
        self.assertIn(order.number, message)
        self.assertIn("190,00", message)
        self.assertIn("Entregar à tarde.", message)
        self.assertIn("Pix", message)

    def test_whatsapp_desativado_ou_sem_numero(self):
        order = self._order()
        config = StoreConfiguration.load()
        config.whatsapp_active = False
        config.save()
        self.assertIsNone(build_whatsapp_url(order, config))
        config.whatsapp_active = True
        config.whatsapp_number = ""
        config.save()
        self.assertIsNone(build_whatsapp_url(order, config))


class OrderTransitionTests(OrderServiceBase):
    def test_transicao_invalida_rejeitada(self):
        order = create_order(
            lines=[CartLineData(product_id=self.product.pk, quantity=1)],
            customer_name="Cliente",
            customer_phone="11987654321",
            note="",
            payment_method=self.payment,
            idempotency_key="t-1",
        )
        order.status = Order.Status.CANCELLED
        order.save()
        with self.assertRaises(ValueError):
            order.transition_to(Order.Status.PAID)
