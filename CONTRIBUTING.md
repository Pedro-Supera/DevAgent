# Contribuindo

Obrigado por considerar uma contribuição.

## Antes de alterar o código

- Leia o `README.md` e `docs/architecture.md`.
- Prefira mudanças pequenas e com responsabilidade bem definida.
- Não introduza execução arbitrária de comandos ou acesso irrestrito ao filesystem sem discussão prévia.

## Desenvolvimento local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Pull requests

Uma PR deve explicar:

- qual problema resolve;
- o que mudou;
- como foi testado;
- qualquer impacto de segurança ou compatibilidade.

Mudanças na política de caminhos, MCP ou análise de arquivos devem incluir testes para os limites de segurança relevantes.
