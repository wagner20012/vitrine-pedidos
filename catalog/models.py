from decimal import Decimal

from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from core.utils import money


class Category(models.Model):
    name = models.CharField("Nome", max_length=120)
    slug = models.SlugField("Slug", max_length=140, unique=True, blank=True)
    description = models.TextField("Descrição", blank=True, default="")
    image = models.ImageField("Imagem", upload_to="categories/", blank=True, null=True)
    order = models.PositiveIntegerField("Ordem", default=0)
    is_active = models.BooleanField("Ativa", default=True)
    created_at = models.DateTimeField("Criada em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizada em", auto_now=True)

    class Meta:
        ordering = ("order", "name")
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:product_list") + f"?categoria={self.slug}"


class Product(models.Model):
    class DiscountType(models.TextChoices):
        NONE = "none", "Sem desconto"
        PERCENT = "percent", "Percentual (%)"
        FIXED = "fixed", "Valor fixo (R$)"

    class StockStatus(models.TextChoices):
        IN_STOCK = "in_stock", "Disponível"
        LOW_STOCK = "low_stock", "Estoque baixo"
        OUT_OF_STOCK = "out_of_stock", "Fora de estoque"
        BACKORDER = "backorder", "Sob encomenda"

    name = models.CharField("Nome", max_length=200)
    slug = models.SlugField("Slug", max_length=220, unique=True, blank=True)
    short_description = models.CharField("Descrição curta", max_length=300, blank=True, default="")
    description = models.TextField("Descrição completa", blank=True, default="")
    category = models.ForeignKey(
        Category, verbose_name="Categoria", on_delete=models.PROTECT, related_name="products"
    )
    price = models.DecimalField("Preço", max_digits=10, decimal_places=2)
    discount_type = models.CharField(
        "Tipo de desconto", max_length=10, choices=DiscountType.choices, default=DiscountType.NONE
    )
    discount_value = models.DecimalField(
        "Valor do desconto", max_digits=10, decimal_places=2, default=0
    )
    stock = models.IntegerField("Estoque", default=0)
    min_stock = models.PositiveIntegerField("Estoque mínimo", default=3)
    allow_backorder = models.BooleanField("Permitir encomenda", default=False)
    is_featured = models.BooleanField("Destaque", default=False)
    is_active = models.BooleanField("Ativo", default=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        ordering = ("-created_at", "name")
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        indexes = [
            models.Index(fields=["is_active", "is_featured"]),
            models.Index(fields=["category", "is_active"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:product_detail", args=[self.slug])

    # ---------------------------------------------------------- preços
    @property
    def discount_amount(self) -> Decimal:
        """Valor monetário do desconto sobre o preço normal."""
        price = money(self.price)
        value = money(self.discount_value)
        if self.discount_type == self.DiscountType.PERCENT:
            return money(price * value / Decimal("100"))
        if self.discount_type == self.DiscountType.FIXED:
            return money(min(value, price))
        return money(0)

    @property
    def final_price(self) -> Decimal:
        return money(self.price - self.discount_amount)

    @property
    def has_discount(self) -> bool:
        return self.discount_amount > 0

    # ---------------------------------------------------------- estoque
    def stock_status(self, reserved: int = 0) -> "Product.StockStatus":
        """Estado de disponibilidade considerando reservas feitas por outras sessões.

        reserved: quantidade já reservada (não inclui a sessão atual).
        """
        from core.models import StoreConfiguration

        available = self.stock - max(reserved, 0)
        if self.allow_backorder and available <= 0:
            return self.StockStatus.BACKORDER
        if available > 0:
            if available <= self.min_stock:
                return self.StockStatus.LOW_STOCK
            return self.StockStatus.IN_STOCK
        config = StoreConfiguration.load()
        if config.allow_order_when_zero_stock:
            return self.StockStatus.BACKORDER
        return self.StockStatus.OUT_OF_STOCK


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, verbose_name="Produto", on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField("Imagem", upload_to="products/")
    alt_text = models.CharField("Texto alternativo", max_length=200, blank=True, default="")
    order = models.PositiveIntegerField("Ordem", default=0)
    is_primary = models.BooleanField("Imagem principal", default=False)
    created_at = models.DateTimeField("Criada em", auto_now_add=True)

    class Meta:
        ordering = ("-is_primary", "order", "id")
        verbose_name = "Imagem do produto"
        verbose_name_plural = "Imagens do produto"

    def __str__(self):
        return f"Imagem de {self.product.name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_primary:
            self.product.images.exclude(pk=self.pk).update(is_primary=False)
        elif not self.product.images.exclude(pk=self.pk).filter(is_primary=True).exists():
            ProductImage.objects.filter(pk=self.pk).update(is_primary=True)
