# Como contribuir

Obrigado pelo interesse em contribuir com Vitrine & Pedidos.

## Antes de começar

1. Confira as issues existentes para evitar trabalho duplicado.
2. Para mudanças grandes, abra uma issue descrevendo o problema e a solução proposta.
3. Não inclua credenciais, dados reais de clientes, banco local ou arquivos de ambiente.

## Fluxo recomendado

1. Crie uma branch com nome descritivo, por exemplo `fix/carrinho-quantidade`.
2. Faça uma mudança pequena e focada.
3. Execute `python manage.py check` e `python manage.py test`.
4. Revise a alteração e confirme que não incluiu segredos ou dados gerados.
5. Abra um Pull Request com contexto, passos de teste e capturas de tela quando forem úteis.

## Padrões do projeto

- Siga os padrões e convenções já usados no código.
- Mantenha regras de preço, desconto e estoque no servidor.
- Preserve validações de permissão e proteção CSRF.
- Atualize a documentação quando alterar instalação, configuração ou comportamento visível.
- Prefira mensagens e rótulos de interface em português brasileiro, salvo quando houver uma razão para outro idioma.

## Pull Requests

Um PR deve explicar o motivo da mudança, resumir o que foi alterado, listar os testes executados e mencionar limitações ou riscos conhecidos. Alterações que afetam pedidos, estoque, autenticação ou dados pessoais exigem atenção especial.
