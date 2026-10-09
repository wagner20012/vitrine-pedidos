from decimal import Decimal

from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory, TestCase

from catalog.models import Category, Product
from orders.services import get_reserved_map, reserve_for_session, CartLineData
from django.utils import timezone
from datetime import timedelta

from cart.services import add_to_cart, load_cart, remove_from_cart, update_quantity
from core.models import StoreConfiguration
from orders.services import OrderError


class CartServiceTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.category = Category.objects.create(name="Maquiagem")
        self.product = Product.objects.create(
            name="Batom",
            category=self.category,
            price=Decimal("50.00"),
            stock=10,
            discount_type=Product.DiscountType.PERCENT,
            discount_value=Decimal("10"),
        )
        self.other = Product.objects.create(
            name="Sombra", category=self.category, price=Decimal("30.00"), stock=5
        )

    def _request(self):
        request = self.factory.get("/")
        request.session = SessionStore()
        request.session.create()
        return request

    def test_adicionar_recalcula_preco_do_banco(self):
        request = self._request()
        add_to_cart(request, self.product.pk, 2)
        cart = load_cart(request)
        self.assertEqual(cart.item_count, 2)
        line = cart.lines[0]
        # Preço vindo do banco com desconto de 10%: R$ 45,00
        self.assertEqual(line.unit_final_price, Decimal("45.00"))
        self.assertEqual(line.subtotal, Decimal("90.00"))
        self.assertEqual(cart.total, Decimal("90.00"))

    def test_totais_com_varios_produtos(self):
        request = self._request()
        add_to_cart(request, self.product.pk, 2)  # 2 x 45 = 90
        add_to_cart(request, self.other.pk, 1)    # 1 x 30 = 30
        cart = load_cart(request)
        self.assertEqual(cart.subtotal, Decimal("130.00"))
        self.assertEqual(cart.discount_total, Decimal("10.00"))
        self.assertEqual(cart.total, Decimal("120.00"))

    def test_nao_permite_estoque_negativo_no_carrinho(self):
        request = self._request()
        add_to_cart(request, self.product.pk, 10)
        with self.assertRaises(OrderError):
            add_to_cart(request, self.product.pk, 1)
        cart = load_cart(request)
        self.assertEqual(cart.item_count, 10)

    def test_produto_inativo_nao_entra_no_carrinho(self):
        request = self._request()
        add_to_cart(request, self.product.pk, 1)
        self.product.is_active = False
        self.product.save()
        cart = load_cart(request)
        self.assertTrue(cart.is_empty)

    def test_reserva_de_outra_sessao_diminui_disponibilidade(self):
        other_session = SessionStore()
        other_session.create()
        reserve_for_session(
            other_session.session_key, [CartLineData(product_id=self.product.pk, quantity=8)]
        )
        request = self._request()
        # Disponível: 10 - 8 reservadas = 2 → tentar 5 falha
        with self.assertRaises(OrderError):
            add_to_cart(request, self.product.pk, 5)
        add_to_cart(request, self.product.pk, 2)
        cart = load_cart(request)
        self.assertEqual(cart.item_count, 2)

    def test_atualizar_e_remover(self):
        request = self._request()
        add_to_cart(request, self.product.pk, 2)
        update_quantity(request, self.product.pk, 4)
        cart = load_cart(request)
        self.assertEqual(cart.item_count, 4)
        remove_from_cart(request, self.product.pk)
        self.assertTrue(load_cart(request).is_empty)
