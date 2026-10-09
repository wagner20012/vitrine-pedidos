from decimal import Decimal

from django.test import TestCase

from catalog.models import Category, Product


class PricingTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Perfumes")
        self.product = Product.objects.create(
            name="Perfume Teste",
            category=self.category,
            price=Decimal("100.00"),
        )

    def test_sem_desconto(self):
        self.assertEqual(self.product.discount_amount, Decimal("0"))
        self.assertEqual(self.product.final_price, Decimal("100.00"))
        self.assertFalse(self.product.has_discount)

    def test_desconto_percentual(self):
        self.product.discount_type = Product.DiscountType.PERCENT
        self.product.discount_value = Decimal("10")
        self.product.save()
        self.assertEqual(self.product.discount_amount, Decimal("10.00"))
        self.assertEqual(self.product.final_price, Decimal("90.00"))

    def test_desconto_fixo(self):
        self.product.discount_type = Product.DiscountType.FIXED
        self.product.discount_value = Decimal("20.00")
        self.product.save()
        self.assertEqual(self.product.discount_amount, Decimal("20.00"))
        self.assertEqual(self.product.final_price, Decimal("80.00"))

    def test_desconto_fixo_nao_ultrapassa_o_preco(self):
        self.product.discount_type = Product.DiscountType.FIXED
        self.product.discount_value = Decimal("150.00")
        self.product.save()
        self.assertEqual(self.product.discount_amount, Decimal("100.00"))
        self.assertEqual(self.product.final_price, Decimal("0"))

    def test_percentual_com_casas_decimais(self):
        self.product.discount_type = Product.DiscountType.PERCENT
        self.product.discount_value = Decimal("12.5")
        self.product.save()
        self.assertEqual(self.product.final_price, Decimal("87.50"))

    def test_slug_gerado_automaticamente(self):
        self.assertEqual(self.product.slug, "perfume-teste")
