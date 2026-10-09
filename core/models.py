from django.db import models


class StoreConfiguration(models.Model):
    """Configurações gerais da loja (registro único, pk=1)."""

    store_name = models.CharField("Nome da loja", max_length=120, default="Minha Loja de Beleza")
    tagline = models.CharField("Slogan", max_length=200, blank=True, default="")

    # Aparência
    logo = models.ImageField("Logo", upload_to="store/", blank=True, null=True)
    favicon = models.ImageField("Favicon", upload_to="store/", blank=True, null=True)
    primary_color = models.CharField("Cor principal", max_length=7, default="#9D174D")
    accent_color = models.CharField("Cor de destaque", max_length=7, default="#D97706")

    # Contato
    phone = models.CharField("Telefone", max_length=30, blank=True, default="")
    email = models.EmailField("E-mail", blank=True, default="")
    address = models.CharField("Endereço", max_length=255, blank=True, default="")
    instagram = models.CharField("Instagram (usuário ou URL)", max_length=120, blank=True, default="")
    business_hours = models.CharField("Horário de atendimento", max_length=200, blank=True, default="")
    service_message = models.TextField("Mensagem de atendimento", blank=True, default="")

    # WhatsApp
    whatsapp_number = models.CharField(
        "Número do WhatsApp",
        max_length=20,
        blank=True,
        default="",
        help_text="Apenas dígitos, com DDD. Ex.: 11987654321",
    )
    whatsapp_message = models.CharField(
        "Mensagem inicial do WhatsApp",
        max_length=200,
        blank=True,
        default="Olá! Gostaria de mais informações sobre um produto.",
    )
    whatsapp_active = models.BooleanField("Botão do WhatsApp ativo", default=True)

    # Estoque / pedidos
    allow_order_when_zero_stock = models.BooleanField(
        "Permitir pedidos quando o estoque chegar a zero",
        default=False,
        help_text="Exibe 'Disponível sob encomenda' para produtos sem estoque.",
    )
    reservation_minutes = models.PositiveSmallIntegerField(
        "Minutos de reserva no checkout",
        default=15,
        help_text="Tempo em que o estoque fica reservado durante o checkout.",
    )

    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Configuração da loja"
        verbose_name_plural = "Configuração da loja"

    def __str__(self):
        return self.store_name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Banner(models.Model):
    title = models.CharField("Título", max_length=120)
    subtitle = models.CharField("Subtítulo", max_length=200, blank=True, default="")
    image = models.ImageField("Imagem", upload_to="banners/")
    button_text = models.CharField("Texto do botão", max_length=60, blank=True, default="")
    link = models.CharField("Link do botão", max_length=300, blank=True, default="")
    order = models.PositiveIntegerField("Ordem", default=0)
    is_active = models.BooleanField("Ativo", default=True)
    created_at = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        ordering = ("order", "id")
        verbose_name = "Banner"
        verbose_name_plural = "Banners"

    def __str__(self):
        return self.title


class AuditLog(models.Model):
    """Registro de ações administrativas importantes."""

    action = models.CharField("Ação", max_length=120)
    user = models.ForeignKey(
        "auth.User", verbose_name="Usuário", null=True, blank=True, on_delete=models.SET_NULL
    )
    object_type = models.CharField("Tipo do objeto", max_length=80, blank=True, default="")
    object_id = models.CharField("ID do objeto", max_length=80, blank=True, default="")
    object_repr = models.CharField("Objeto", max_length=255, blank=True, default="")
    details = models.TextField("Detalhes", blank=True, default="")
    created_at = models.DateTimeField("Data", auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Registro de auditoria"
        verbose_name_plural = "Registros de auditoria"

    def __str__(self):
        return f"{self.action} — {self.object_repr} ({self.created_at:%d/%m/%Y %H:%M})"

    @classmethod
    def log(cls, action, obj=None, user=None, details=""):
        return cls.objects.create(
            action=action,
            user=user if getattr(user, "is_authenticated", False) else None,
            object_type=obj.__class__.__name__ if obj is not None else "",
            object_id=str(getattr(obj, "pk", "") or ""),
            object_repr=str(obj)[:255] if obj is not None else "",
            details=details,
        )
