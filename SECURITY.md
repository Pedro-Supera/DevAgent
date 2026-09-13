# Segurança

## Escopo

O DevAgent é atualmente direcionado a uso local/trusted. A camada MCP possui uma política de caminhos para limitar o acesso às raízes autorizadas.

## Reportando problemas

Não publique chaves, tokens, dados pessoais, caminhos privados ou provas de conceito contendo segredos em issues públicas.

Para vulnerabilidades que possam permitir acesso fora das raízes autorizadas, execução de código ou exposição de dados, descreva o problema de forma responsável por um canal privado disponível no perfil do mantenedor.

## Princípios de segurança

- validar caminhos antes de acessar o filesystem;
- resolver symlinks antes de aplicar a allowlist;
- manter a política de caminhos centralizada;
- não executar o código-fonte submetido ao AST analyzer;
- adicionar testes para novas fronteiras de segurança.
