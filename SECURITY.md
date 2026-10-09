# Segurança

## Estado do projeto

Esta aplicação está em fase de testes e preparação para hospedagem. Não envie dados reais de clientes nem a utilize para transações comerciais críticas antes de concluir a revisão de segurança e operação.

## Boas práticas para quem administra o repositório

- Mantenha `SECRET_KEY`, credenciais de banco, tokens e outros segredos fora do Git.
- Nunca publique `.env`, `db.sqlite3`, logs, backups ou uploads privados.
- Use `DEBUG=False`, HTTPS e hosts/origens confiáveis em ambientes públicos.
- Utilize senhas fortes e contas individuais para a administração.
- Mantenha dependências atualizadas e execute os testes antes de publicar mudanças.
- Faça backups do banco e teste periodicamente a restauração.
- Limite o acesso aos dados pessoais e estabeleça prazo de retenção.

## Como reportar uma vulnerabilidade

Não publique detalhes exploráveis de uma vulnerabilidade em uma issue pública. Até existir um canal privado de segurança formal para o projeto, entre em contato diretamente com o mantenedor por um canal privado que ele tenha informado. Inclua passos de reprodução, impacto observado e uma forma segura de retorno. Não inclua dados pessoais, senhas ou segredos no relato.
