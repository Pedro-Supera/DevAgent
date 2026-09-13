# DevAgent

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Version](https://img.shields.io/badge/version-v0.2.1-brightgreen)
![Tests](https://github.com/Pedro-Supera/DevAgent/actions/workflows/tests.yml/badge.svg?branch=main)
![License](https://img.shields.io/badge/license-MIT-blue)

**DevAgent v0.2.1** é um analisador/scanner de projetos Python. Oferece uma varredura estruturada e segura, exportação em JSON e árvore textual, estatísticas por extensão, uma interface gráfica em CustomTkinter e um servidor MCP reutilizável.

O DevAgent é uma ferramenta de inspeção de projetos Python. Ele ajuda a entender a estrutura de um diretório, identificar arquivos, extensões e tamanhos, e exportar essas informações de forma programática. Funcionalidades de análise avançada e integração com IA fazem parte do roadmap.

## Status e versão

- **Versão:** `0.2.1`
- **Licença:** MIT
- **Python mínimo:** `>=3.10`

O foco desta release é a base de scanner, GUI e MCP. Não é um agente autônomo. Análises baseadas em AST e IA estão planejadas para versões futuras.

## Funcionalidades atuais

- Scanner tipado de projetos Python.
- Varredura segura sem seguir links simbólicos que fogem da raiz.
- Exclusões de segurança padrão (`.env`, `.git`, `__pycache__`, `venv`, etc.) e suporte ao `.gitignore` da raiz analisada.
- Modelos de dados validados e serialização JSON/árvore textual.
- Interface gráfica CustomTkinter com tema escuro, seleção de pasta, progresso e abas de resultados.
- Servidor MCP com ferramentas `escanear_projeto` e `obter_arvore_projeto`.

## Arquitetura

- `devagent/scanner.py`: varredura segura e regras de exclusão.
- `devagent/models.py`: modelos tipados e métricas de resultado.
- `devagent/gui/app.py`: interface gráfica CustomTkinter.
- `devagent/mcp_server.py`: servidor MCP.
- `devagent/exceptions.py`: exceções de domínio.

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Execução da GUI

```bash
python -m devagent.gui.app
```

Ou, se instalado via script:

```bash
devagent
```

## Execução dos testes

```bash
pytest
```

## Servidor MCP

```bash
python -m devagent.mcp_server
```

O servidor expõe as ferramentas `escanear_projeto` e `obter_arvore_projeto`.

## Exemplo de uso da API Python

```python
from devagent.scanner import ProjectScanner
from pathlib import Path

scanner = ProjectScanner(Path("/caminho/do/projeto"))
resultado = scanner.escanear()

print(resultado.total_arquivos)
print(resultado.total_diretorios)
print(resultado.estatisticas_extensao)
print(resultado.para_arvore_texto())
print(resultado.para_json())
```

## Segurança

- A varredura respeita exclusões de ambiente, build e cache.
- Links simbólicos externos à raiz não são seguidos.
- Arquivos inacessíveis são ignorados em vez de interromper a análise.
- O `.gitignore` da raiz é aplicado quando disponível.

## Roadmap

- **v0.2.1** — base funcional de scanner, GUI e MCP. O badge da GUI permanece como `v0.2.0` nesta etapa.
- **v0.3.0** — parser AST, cache e integrações de análise avançada/IA.

## Contribuição

1. Abra uma issue para discutir mudanças significativas.
2. Execute `pytest` antes de enviar pull requests.
3. Mantenha a versão em `pyproject.toml`, `devagent/__init__.py` e `README.md` sincronizada.

## Licença

MIT — veja o arquivo [LICENSE](LICENSE).

