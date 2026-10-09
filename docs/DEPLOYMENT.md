# Guia de implantação

Este documento descreve os cuidados para publicar a aplicação em uma plataforma de hospedagem. A implantação não deve ser considerada concluída até que os testes pós-publicação sejam feitos.

## Antes de começar

- Tenha o código no GitHub em um repositório sem banco local, arquivos `.env`, logs ou dados pessoais.
- Escolha um serviço que suporte aplicações Python/Django e PostgreSQL.
- Planeje armazenamento persistente para fotos de produtos, categorias e banners. Em várias plataformas, arquivos gravados no disco local da aplicação podem desaparecer em uma nova implantação ou reinicialização.
- Não utilize dados reais de clientes enquanto a instância estiver em fase de teste.

## Configurações necessárias

Configure as variáveis no painel da hospedagem, sem colocá-las no código ou em arquivos públicos:

| Variável | Valor esperado |
|---|---|
| `SECRET_KEY` | Chave aleatória forte e exclusiva para o ambiente |
| `DEBUG` | `False` |
| `DATABASE_URL` | URL privada do PostgreSQL fornecida pela hospedagem |
| `ALLOWED_HOSTS` | Hostnames reais separados por vírgula, sem protocolo |
| `CSRF_TRUSTED_ORIGINS` | Origens completas com `https://`, separadas por vírgula |
| `SESSION_COOKIE_SECURE` | `True` em HTTPS |
| `CSRF_COOKIE_SECURE` | `True` em HTTPS |
| `SECURE_SSL_REDIRECT` | `True` quando HTTPS estiver corretamente configurado |

Não reutilize a chave secreta do computador local. Não publique valores dessas variáveis em capturas de tela ou logs.

## Comandos típicos de implantação

O ambiente deve instalar as dependências de `requirements.txt`, aplicar as migrações e coletar os arquivos estáticos. Para um servidor WSGI com Gunicorn, o comando de inicialização é:

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

O comando de build normalmente precisa executar:

```bash
python manage.py collectstatic --noinput
python manage.py migrate --noinput
```

Confirme a sintaxe e as variáveis exigidas pelo provedor escolhido antes de usar esses comandos. Não execute migrações destrutivas em um banco com dados sem backup.

## Conta administrativa

Crie uma conta administrativa exclusiva para o ambiente hospedado. Não use senha de demonstração nem compartilhe uma conta entre testadores. Conceda acesso apenas a quem realmente precisa.

## Fotos e uploads

O projeto utiliza `MEDIA_ROOT` para arquivos enviados. Antes de aceitar uploads na hospedagem, configure um disco persistente compatível com o provedor ou um serviço de armazenamento de objetos. Sem isso, imagens carregadas pelo painel podem deixar de existir após uma nova implantação.

## Checklist após publicar

- [ ] A página inicial abre por HTTPS.
- [ ] `DEBUG=False` e a chave secreta é exclusiva.
- [ ] `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` correspondem ao domínio.
- [ ] Migrações foram aplicadas sem erro.
- [ ] Arquivos estáticos carregam corretamente.
- [ ] Foi possível entrar no painel com uma conta administrativa segura.
- [ ] Um produto fictício pode ser criado, editado e exibido.
- [ ] Carrinho, checkout, criação do pedido e link do WhatsApp foram testados.
- [ ] Estoque e cancelamento de pedido foram verificados.
- [ ] Uploads continuam disponíveis após uma nova implantação.
- [ ] Backup e restauração do banco foram planejados e testados.
- [ ] Logs não expõem segredos nem dados pessoais desnecessários.

## Limitações a avaliar antes de produção

O projeto está em fase de testes. A publicação técnica não substitui auditoria de segurança, revisão de privacidade/LGPD, testes de carga, monitoramento, política de backup ou validação dos fluxos comerciais. A conclusão do pedido abre uma conversa no WhatsApp; não representa confirmação automática de pagamento.
