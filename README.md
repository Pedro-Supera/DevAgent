# DevAgent

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Version](https://img.shields.io/badge/version-v0.3.0-brightgreen)
![Tests](https://github.com/Pedro-Supera/DevAgent/actions/workflows/tests.yml/badge.svg?branch=main)
![License](https://img.shields.io/badge/license-MIT-blue)

> **Developer tooling para inspeção segura de projetos Python.**

O **DevAgent** é uma ferramenta de engenharia de software para inspecionar projetos Python sem executar o código analisado. Ele combina **scanner de arquivos, análise AST, política de caminhos, modelos tipados, GUI e servidor MCP** em uma arquitetura modular.

O projeto foi construído para servir como uma base confiável para futuras ferramentas assistidas por IA: primeiro os dados são coletados e validados por ferramentas determinísticas; depois um agente pode raciocinar sobre esses resultados.

**Status:** `v0.3.0` · **Python:** `>=3.10` · **Licença:** MIT

## Por que o DevAgent existe?

Projetos Python rapidamente ficam difíceis de entender quando possuem muitos arquivos, módulos e dependências. Antes de pedir para uma IA modificar um projeto, é útil ter uma representação estruturada e segura do que realmente existe nele.

O DevAgent resolve a parte de **inspeção**:

```text
Projeto Python
     │
     ▼
 Scanner seguro ──────► estrutura / arquivos / extensões / tamanhos
     │
     ▼
 Política de caminhos ─► restringe o que pode ser acessado
     │
     ▼
 AST Analyzer ─────────► imports / classes / funções / chamadas
     │
     ▼
 Modelos tipados ──────► resultados estruturados
     │
     ├────────► GUI
     │
     └────────► MCP ─────────► cliente/agent de IA
```

> O DevAgent **não é um agente autônomo** nesta versão. A arquitetura foi deliberadamente construída para separar ferramentas determinísticas da camada de raciocínio.

## O que ele faz

- **Scanner tipado:** percorre projetos e produz uma representação estruturada.
- **Varredura segura:** não segue links simbólicos que escapam da raiz analisada.
- **Exclusões:** respeita exclusões de ambiente/build/cache e o `.gitignore` da raiz.
- **AST estático:** identifica imports, classes, métodos, funções, decorators e chamadas sem importar ou executar o arquivo.
- **Modelos de dados:** resultados serializáveis em JSON e árvore textual.
- **GUI:** interface CustomTkinter para seleção de pasta, progresso e visualização dos resultados.
- **MCP:** expõe ferramentas reutilizáveis para clientes compatíveis.
- **Testes:** cobertura de scanner, AST, contratos MCP e política de caminhos.

## Arquitetura

| Módulo | Responsabilidade |
|---|---|
| `devagent/scanner.py` | Varredura, filtros e estrutura do projeto |
| `devagent/path_policy.py` | Allowlist de raízes e validação de caminhos |
| `devagent/models.py` | Modelos tipados e serialização |
| `devagent/ast_analyzer.py` | Análise estrutural com `ast` da biblioteca padrão |
| `devagent/mcp_server.py` | Exposição das ferramentas via MCP |
| `devagent/gui/app.py` | Interface gráfica |
| `devagent/exceptions.py` | Exceções de domínio |

Veja também [`docs/architecture.md`](docs/architecture.md) para a visão detalhada.

## Segurança

A segurança de acesso ao filesystem é tratada como parte da arquitetura, não como uma validação espalhada pelas ferramentas.

- `DEVAGENT_ALLOWED_ROOTS` define as raízes permitidas pelo servidor MCP.
- Quando a variável não é definida, o diretório de trabalho do servidor é a raiz permitida.
- Caminhos são normalizados e resolvidos antes da validação.
- `..` não permite escapar da allowlist.
- Symlinks externos à raiz são rejeitados.
- Caminhos inexistentes ou do tipo incorreto são rejeitados pela política quando aplicável.
- O analisador AST usa `ast.parse()` e `ast.NodeVisitor`; o código analisado não é importado nem executado.

**Escopo atual:** uso local/trusted. Autenticação, identidade e isolamento de processos não fazem parte desta versão.

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## GUI

```bash
python -m devagent.gui.app
```

Ou, quando o entry point estiver instalado:

```bash
devagent
```

## Testes

```bash
pytest
```

Os testes são executados também pelo GitHub Actions em cada alteração relevante da branch `main`.

## Servidor MCP

```bash
python -m devagent.mcp_server
```

Ferramentas expostas:

- `escanear_projeto`
- `obter_arvore_projeto`
- `analisar_arquivo_python`

### Política de acesso MCP

Exemplo Linux:

```bash
export DEVAGENT_ALLOWED_ROOTS="$HOME/projetos:$HOME/repos"
python -m devagent.mcp_server
```

A ideia é simples: **o cliente MCP não ganha acesso arbitrário ao filesystem só porque conhece um caminho**.

## Exemplo Python

```python
from pathlib import Path
from devagent.scanner import ProjectScanner

scanner = ProjectScanner(Path("/caminho/do/projeto"))
resultado = scanner.escanear()

print(resultado.total_arquivos)
print(resultado.total_diretorios)
print(resultado.estatisticas_extensao)
print(resultado.para_arvore_texto())
```

Análise AST sem executar o arquivo:

```python
from pathlib import Path
from devagent.ast_analyzer import analisar_arquivo

resultado = analisar_arquivo(Path("/caminho/arquivo.py"))
print(resultado.classes)
print(resultado.funcoes)
print(resultado.chamadas)
print(resultado.erro)
```

## Roadmap

### v0.3.x — base de inspeção

- scanner seguro
- análise AST
- MCP
- política centralizada de caminhos
- testes de segurança

### v0.4 — Project Intelligence

A próxima evolução está documentada em [#1](https://github.com/Pedro-Supera/DevAgent/issues/1): aumentar a capacidade de inspeção antes de adicionar automação destrutiva.

1. listar arquivos relevantes;
2. ler arquivos com limites controlados;
3. agregar informações do projeto Python;
4. executar testes de forma controlada;
5. permitir que agentes raciocinem sobre resultados estruturados;
6. somente depois avaliar edição automática com validação e rollback.

**Fora do escopo por enquanto:** execução arbitrária de shell, edição automática sem validação, agente autônomo e RAG/vector DB sem necessidade demonstrada.

O objetivo é evitar transformar o projeto em um agente autônomo difícil de controlar antes de existir uma base sólida.

## Contribuição

Consulte [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licença

MIT — veja [`LICENSE`](LICENSE).

---

Desenvolvido por [Pedro-Supera](https://github.com/Pedro-Supera) como projeto de estudo e engenharia de software.
