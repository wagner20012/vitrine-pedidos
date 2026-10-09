from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Product
from core.models import StoreConfiguration
from orders.models import PaymentMethod


def _create_product(**kwargs):
    category, _ = Category.objects.get_or_create(name="Teste")
    defaults = dict(
        name="Produto Loja",
        category=category,
        price=Decimal("50.00"),
        stock=10,
    )
    defaults.update(kwargs)
    return Product.objects.create(**defaults)


class StoreFlowTests(TestCase):
    def setUp(self):
        self.product = _create_product()
        StoreConfiguration.load()

    def test_home_abre(self):
        response = self.client.get(reverse("catalog:home"))
        self.assertEqual(response.status_code, 200)

    def test_lista_e_detalhe(self):
        response = self.client.get(reverse("catalog:product_list"))
        self.assertContains(response, self.product.name)
        response = self.client.get(self.product.get_absolute_url())
        self.assertContains(response, self.product.name)

    def test_busca_por_nome(self):
        response = self.client.get(reverse("catalog:product_list") + "?q=loja")
        self.assertContains(response, self.product.name)
        response = self.client.get(reverse("catalog:product_list") + "?q=inexistente")
        self.assertContains(response, "Nenhum produto")

    def test_checkout_vazio_redireciona(self):
        response = self.client.get(reverse("orders:checkout"))
        self.assertEqual(response.status_code, 302)

    def test_fluxo_completo_de_pedido(self):
        """Carrinho -> checkout -> pedido criado -> confirmação com número."""
        self.payment = PaymentMethod.objects.create(name="Pix")
        session = self.client.session
        session["beauty_cart"] = {str(self.product.pk): 2}
        session.save()

        response = self.client.get(reverse("orders:checkout"))
        self.assertEqual(response.status_code, 200)
        key = response.context["form"].initial["idempotency_key"]

        response = self.client.post(
            reverse("orders:checkout"),
            {
                "customer_name": "Maria Teste",
                "customer_phone": "(11) 91234-5678",
                "note": "Teste",
                "payment_method": self.payment.pk,
                "idempotency_key": key,
            },
        )
        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse("orders:confirmation"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PED-")

        # Preço recalculado no servidor: 2 x 50 = 100, sem desconto
        from orders.models import Order

        order = Order.objects.get()
        self.assertEqual(order.total, Decimal("100.00"))
        self.assertEqual(order.customer_name, "Maria Teste")

    def test_preco_malicioso_do_navegador_e_ignorado(self):
        """O backend nunca confia em valores enviados pelo cliente."""
        self.payment = PaymentMethod.objects.create(name="Pix")
        session = self.client.session
        session["beauty_cart"] = {str(self.product.pk): 1}
        session.save()

        response = self.client.get(reverse("orders:checkout"))
        key = response.context["form"].initial["idempotency_key"]
        self.client.post(
            reverse("orders:checkout"),
            {
                "customer_name": "Atacante",
                "customer_phone": "11987654321",
                "note": "",
                "payment_method": self.payment.pk,
                "idempotency_key": key,
                # tentativa de manipulação (campo extra não usado pelo servidor):
                "price": "0.01",
                "total": "0.01",
            },
        )
        from orders.models import Order

        order = Order.objects.get()
        self.assertEqual(order.total, Decimal("50.00"))


class SecurityTests(TestCase):
    def setUp(self):
        self.product = _create_product()

    def test_painel_exige_login(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_painel_exige_staff(self):
        User.objects.create_user(username="comum", password="senha-forte-123")
        self.client.login(username="comum", password="senha-forte-123")
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 403)

    def test_staff_acessa_painel(self):
        User.objects.create_user(username="admin", password="senha-forte-123", is_staff=True)
        self.client.login(username="admin", password="senha-forte-123")
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)

    def test_confirmacao_requer_pedido_na_sessao(self):
        response = self.client.get(reverse("orders:confirmation"))
        self.assertEqual(response.status_code, 302)

    def test_whatsapp_retry_requer_sessao(self):
        from orders.models import Order, PaymentMethod

        payment = PaymentMethod.objects.create(name="Pix")
        order = Order.objects.create(
            customer_name="X", customer_phone="119", total=Decimal("10"), payment_method=payment
        )
        response = self.client.post(reverse("orders:whatsapp_retry", args=[order.pk]))
        # Sem o pedido na sessão, acesso negado (redireciona para home).
        self.assertEqual(response.status_code, 302)
