from django.core.management.base import BaseCommand

from catalog.management.commands import _seed


class Command(BaseCommand):
    help = "Popula a loja com dados de demonstração (categorias, produtos, banners, pagamentos)."

    def add_arguments(self, parser):
        parser.add_argument("--sem-imagens", action="store_true", help="Não gerar imagens de demonstração")

    def handle(self, *args, **options):
        created = _seed.run(generate_images=not options["sem_imagens"], stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS(f"Pronto. {created} produtos de demonstração criados."))
