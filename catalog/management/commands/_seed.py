"""Dados de demonstração compartilhados pelo comando seed_demo.

As imagens são geradas localmente com Pillow (gradientes suaves com as
iniciais do produto) — nenhuma imagem protegida é utilizada.
"""

import random

from django.core.files.base import ContentFile
from django.utils.text import slugify

from catalog.models import Category, Product
from core.models import Banner, StoreConfiguration
from orders.models import PaymentMethod

PALETTES = [
    ((157, 23, 77), (251, 207, 232)),
    ((180, 83, 9), (254, 235, 200)),
    ((6, 95, 70), (209, 250, 229)),
    ((30, 64, 175), (219, 234, 254)),
    ((88, 28, 135), (237, 233, 254)),
    ((159, 18, 57), (254, 228, 226)),
    ((146, 64, 14), (254, 243, 199)),
    ((21, 94, 117), (207, 250, 254)),
]

CATEGORIES = [
    ("Perfumes", "Fragrâncias marcantes para todas as ocasiões."),
    ("Maquiagem", "Batom, base, sombra e muito mais."),
    ("Cuidados com a pele", "Hidratantes, séruns e cremes faciais."),
    ("Corpo e banho", "Sabonetes, esfoliantes e hidratantes corporais."),
    ("Cabelos", "Shampoos, máscaras e finalizadores."),
    ("Desodorantes", "Proteção e frescor durante todo o dia."),
    ("Kits", "Combinações especiais com preço especial."),
    ("Presentes", "Para surpreender quem você ama."),
]

PRODUCTS = [
    ("Perfume Floral", "Perfumes", "89.90", "Eau de parfum 50ml com notas de jasmim e âmbar.", "Uma fragrância feminina e sofisticada com saída de bergamota, corpo floral de jasmim e sambac e fundo quente de âmbar e sândalo. Fixação prolongada para o dia inteiro.", 40, True, "percent", "10"),
    ("Body Splash Vanila", "Corpo e banho", "39.90", "Body splash 250ml baunilha e caramelo.", "Refresca e perfuma a pele com uma mistura suave de baunilha, caramelo e leite de coco. Ideal para o dia a dia, com toque delicado e aroma acolhedor.", 60, False, "none", "0"),
    ("Batom Nude", "Maquiagem", "29.90", "Batom matte cremoso tom nude.", "Textura cremosa de acabamento matte que desliza facilmente e mantém a cor por horas. Tom nude universal que valoriza todos os tons de pele.", 80, True, "percent", "20"),
    ("Hidratante Corporal", "Corpo e banho", "45.90", "Loção corporal 400ml manteiga de cacau.", "Absorção rápida com manteiga de cacau e vitamina E. Deixa a pele macia, nutrida e com brilho saudável, sem sensação pegajosa.", 35, False, "fixed", "10"),
    ("Kit Cuidados Completo", "Kits", "129.90", "Shampoo + condicionador + máscara.", "Kit completo de cuidados capilares: shampoo suave, condicionador desembaraçante e máscara de tratamento intensiva para fios saudáveis e brilhantes.", 20, True, "percent", "15"),
    ("Desodorante Roll-on", "Desodorantes", "18.90", "Roll-on 70ml proteção 48h.", "Proteção antitranspirante por até 48 horas, sem álcool. Fragrância leve e fresca, aprovação dermatológica.", 100, False, "none", "0"),
    ("Creme Facial Anti-Idade", "Cuidados com a pele", "79.90", "Creme noturno 50g com retinol.", "Fórmula com retinol encapsulado e ácido hialurônico que suaviza linhas finas e melhora a firmeza da pele durante o sono.", 25, True, "percent", "25"),
    ("Pó Compacto Natural", "Maquiagem", "34.90", "Pó facial translúcido 10g.", "Acabamento natural que controla a oleosidade e fixa a maquiagem. Embalagem compacta com espelho para retoques.", 50, False, "none", "0"),
    ("Água Micelar", "Cuidados com a pele", "27.90", "Água micelar 300ml 3 em 1.", "Limpa, remove maquiagem e tonifica em um único passo. Fórmula suave para todos os tipos de pele, inclusive sensível.", 70, False, "percent", "10"),
    ("Perfume Masculino Intense", "Perfumes", "149.90", "Eau de toilette 100ml amadeirado.", "Fragrância masculina amadeirada e intensa com notas de bergamota, pimenta e vetiver. Ideal para ocasiões especiais.", 15, True, "fixed", "30"),
    ("Máscara Capilar Reconstrutora", "Cabelos", "42.90", "Máscara 300g queratina vegetal.", "Reconstrução profunda com queratina vegetal e óleo de argan. Reduz o frizz e devolve a força aos fios danificados.", 30, False, "none", "0"),
    ("Esponja de Maquiagem", "Maquiagem", "12.90", "Esponja de maquiagem de alta cobertura.", "Esponja macia de alta densidade para aplicação uniforme de base e corretivo. Latex-free.", 120, False, "none", "0"),
    ("Óleo Corporal Iluminador", "Corpo e banho", "49.90", "Óleo corporal 120ml com mica.", "Óleo seco iluminador com partículas de mica dourada. Hidrata e dá um brilho radiante à pele para ocasiões especiais.", 28, False, "percent", "30"),
    ("Presente: Coffret Charme", "Presentes", "99.90", "Coffret com perfume e body lotion.", "Coffret elegante com miniatura de eau de parfum floral e body lotion perfumado, embalado em caixa presenteável com laço.", 18, True, "percent", "12"),
    ("Sérum Vitamina C", "Cuidados com a pele", "64.90", "Sérum antioxidante 30ml vitamina C 10%.", "Antioxidante com vitamina C estabilizada que uniformiza o tom, ilumina e protege a pele dos radicais livres.", 22, False, "none", "0"),
    ("Kit Presente Relaxante", "Presentes", "89.90", "Vela + óleo de banho + sabonete.", "Kit para um momento de autocuidado: vela aromática, óleo de banho e sabonete artesanal em embalagem especial.", 14, False, "fixed", "15"),
]

PAYMENTS = [("Pix", 0), ("Cartão de crédito", 1), ("Cartão de débito", 2), ("Dinheiro", 3), ("Transferência", 4)]


def generate_image(product, palette):
    from PIL import Image, ImageDraw, ImageFont

    start, end = palette
    size = 600
    img = Image.new("RGB", (size, size))
    draw = ImageDraw.Draw(img)
    for y in range(size):
        ratio = y / size
        color = tuple(int(start[i] + (end[i] - start[i]) * ratio) for i in range(3))
        draw.line([(0, y), (size, y)], fill=color)
    # Iniciais do produto
    initials = "".join(word[0] for word in product.split()[:2]).upper()
    try:
        font = ImageFont.truetype("arial.ttf", 180)
    except OSError:
        font = ImageFont.load_default()
    text_color = tuple(min(255, c + 120) for c in start)
    bbox = draw.textbbox((0, 0), initials, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - w) / 2 - bbox[0], (size - h) / 2 - bbox[1]), initials, fill="white", font=font)
    from io import BytesIO

    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    filename = slugify(product)[:40] + ".jpg"
    return ContentFile(buffer.getvalue(), name=filename)


def run(generate_images=True, stdout=None):
    import sys

    out = stdout or sys.stdout

    StoreConfiguration.load()
    config = StoreConfiguration.load()
    config.whatsapp_active = True
    if not config.whatsapp_number:
        config.whatsapp_number = "11999990000"
    config.save()

    categories = {}
    for name, description in CATEGORIES:
        category, _ = Category.objects.get_or_create(name=name, defaults={"description": description})
        categories[name] = category

    for payment_name, order in PAYMENTS:
        PaymentMethod.objects.get_or_create(name=payment_name, defaults={"order": order})

    random.seed(42)
    created = 0
    for index, (name, category, price, short_desc, desc, stock, featured, discount_type, discount_value) in enumerate(PRODUCTS):
        product, was_created = Product.objects.get_or_create(
            name=name,
            defaults={
                "slug": slugify(name),
                "category": categories[category],
                "short_description": short_desc,
                "description": desc,
                "price": price,
                "stock": stock,
                "min_stock": 5,
                "is_featured": featured,
                "discount_type": discount_type,
                "discount_value": discount_value,
            },
        )
        if was_created:
            created += 1
            if generate_images:
                palette = PALETTES[index % len(PALETTES)]
                content = generate_image(name, palette)
                product.images.create(image=content, alt_text=f"Imagem de {name}", is_primary=True)

    if not Banner.objects.exists():
        banner = Banner.objects.create(
            title="Beleza que inspira",
            subtitle="Descubra produtos selecionados para realçar sua beleza natural.",
            button_text="Ver produtos",
            link="/produtos/",
            order=0,
        )
        if generate_images:
            content = generate_image("Beleza que inspira", PALETTES[0])
            banner.image.save("banner-1.jpg", content, save=True)

    return created
