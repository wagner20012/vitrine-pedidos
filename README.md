<div align="center">

# Vitrine & Pedidos

**Plataforma web de catálogo, estoque e pedidos para pequenas lojas.**

[Funcionalidades](#-funcionalidades) · [Tecnologias](#-tecnologias) · [Executar localmente](#-executar-localmente) · [Documentação](#-documentação) · [Segurança](#-segurança)

</div>

---

## Sobre o projeto

Vitrine & Pedidos é uma aplicação web desenvolvida em Django para organizar uma vitrine digital, gerenciar produtos e estoque e registrar pedidos. O cliente pode navegar pelo catálogo, montar um carrinho e iniciar o contato para concluir o pedido pelo WhatsApp. A equipe administra produtos, pedidos e configurações por áreas protegidas por autenticação.

> **Status:** projeto em fase de testes e preparação para hospedagem. Antes de utilizar em produção, revise as configurações de implantação, armazenamento de imagens, backups, privacidade e segurança.

## ✨ Funcionalidades

### Loja
- Página inicial com banners, categorias, destaques e promoções.
- Catálogo com pesquisa, filtros, ordenação e paginação.
- Páginas de produto com imagens, preços, descontos e disponibilidade.
- Carrinho de compras baseado em sessão, com valores recalculados no servidor.
- Checkout sem exigir criação de conta do cliente.
- Registro do pedido antes de abrir o WhatsApp e página de confirmação.

### Gestão
- Painel interno em `/painel/`, reservado a usuários autorizados.
- Cadastro e gerenciamento de produtos, categorias, imagens e estoque.
- Gestão de pedidos e seus estados, com registro de cancelamentos.
- Formas de pagamento e configurações da loja.
- Relatórios e ferramentas de desconto em massa.
- Administração Django em `/django-admin/`.

### Confiabilidade e experiência
- Validação de preços e descontos no backend.
- Transações para operações de estoque e proteção contra estoque negativo.
- Registro de informações dos itens no momento do pedido.
- Registro de ações administrativas e validações de acesso.
- URLs amigáveis, sitemap e página de privacidade.

> A integração com WhatsApp direciona o cliente para continuar a conversa. Este projeto não deve ser entendido como integração automática com um gateway de pagamento.

## 🧰 Tecnologias

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.12+ |
| Aplicação web | Django 5.x |
| Interface | HTML, CSS, JavaScript e Tailwind CSS via CDN |
| Banco local | SQLite |
| Banco para hospedagem | PostgreSQL, via `DATABASE_URL` |
| Arquivos estáticos | WhiteNoise |
| Imagens | Pillow |

## 🚀 Executar localmente

### Opção simples no Windows

1. Instale Python 3.12 ou superior, se ainda não estiver instalado.
2. Baixe o código e extraia a pasta.
3. Dê dois cliques em `INICIAR.bat`.
4. Aguarde a instalação e a inicialização do servidor.
5. Abra `http://127.0.0.1:8000/` no navegador.

O primeiro início pode levar alguns minutos, pois o script cria o ambiente virtual e instala as dependências. Mantenha a janela do servidor aberta enquanto estiver usando a aplicação.

### Endereços locais

- Loja: `http://127.0.0.1:8000/`
- Painel interno: `http://127.0.0.1:8000/painel/`
- Administração Django: `http://127.0.0.1:8000/django-admin/`

O usuário administrativo deve ser criado no ambiente local com `python manage.py createsuperuser`. Não há credenciais administrativas padrão documentadas neste repositório.

### Execução manual (opcional)

```bash
python -m venv venv
# Windows
venv\\Scripts\\activate
# Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

No Windows, `copy` é um comando do Prompt de Comando. No PowerShell, também é possível usar `Copy-Item .env.example .env`. Gere uma `SECRET_KEY` exclusiva e configure-a no `.env` para ambientes próprios. Para popular a loja com conteúdo fictício de demonstração, execute `python manage.py seed_demo`; para não gerar imagens, acrescente `--sem-imagens`.

## 🧪 Testes e verificações

Com as dependências instaladas, execute:

```bash
python manage.py check
python manage.py test
```

Os testes automatizados cobrem áreas como catálogo, carrinho, cálculo de descontos, pedidos, estoque e permissões. Execute-os após mudanças e confira também manualmente os fluxos de compra antes de publicar uma versão. O workflow do GitHub Actions executa verificações automatizadas a cada push e pull request.

## 📚 Documentação

- [Guia de configuração e implantação](docs/DEPLOYMENT.md)
- [Segurança e reporte responsável](SECURITY.md)
- [Como contribuir](CONTRIBUTING.md)
- [Suporte e perguntas frequentes](SUPPORT.md)
- [Histórico de alterações](CHANGELOG.md)

## 🔐 Segurança e dados

- Nunca envie `.env`, senhas, tokens, chaves secretas, banco local ou dados reais de clientes para o GitHub.
- Use variáveis de ambiente na hospedagem e mantenha `DEBUG=False` em produção.
- Configure `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` para o domínio real.
- Defina um plano de backup e teste a restauração do banco.
- Planeje o armazenamento persistente das imagens enviadas pelo painel; o disco de uma hospedagem pode ser temporário.
- Use apenas dados fictícios durante demonstrações públicas.

Leia [SECURITY.md](SECURITY.md) antes de publicar ou compartilhar uma instância acessível pela internet.

## 🗺️ Estrutura do projeto

```text
config/       Configurações, URLs e entrada WSGI/ASGI
core/         Configuração da loja, banners, auditoria e utilitários
catalog/      Categorias, produtos, catálogo e sitemap
cart/         Carrinho e regras de cálculo
orders/       Checkout, pedidos, estoque reservado e WhatsApp
customers/    Cadastro básico de clientes
dashboard/    Painel interno, gestão e relatórios
templates/    Templates HTML da loja e do painel
static/       CSS e JavaScript próprios
docs/         Guias de operação e implantação
.github/      Automação e modelos de colaboração
```

## 🧭 Roteiro do projeto

- [x] Catálogo e páginas de produto
- [x] Carrinho e criação de pedidos
- [x] Gestão administrativa e estoque
- [x] Testes automatizados iniciais
- [ ] Revisão de implantação e monitoramento em hospedagem
- [ ] Definição de armazenamento persistente para imagens
- [ ] Revisão final de segurança, privacidade, backups e acessibilidade
- [ ] Decisão e inclusão de uma licença de uso

## Licença

Ainda não foi definida uma licença para este projeto. Até que uma licença seja adicionada pelo titular, não presuma autorização para copiar, redistribuir ou utilizar o código em outros projetos.

---

<div align="center">

Desenvolvido para simplificar a gestão de uma vitrine digital e seus pedidos.

</div>
