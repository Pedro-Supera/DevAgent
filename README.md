# DevAgent

**DevAgent v0.2.0** é um analisador inteligente de projetos Python. Ele oferece um scanner tipado, exportação em JSON e árvore textual, estatísticas por extensão, servidor MCP reutilizável e uma interface gráfica moderna em CustomTkinter com tema escuro inspirado no GitHub.

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Testes

```bash
pytest
```

## Interface gráfica

```bash
python -m devagent.gui.app
```

A GUI oferece:

- **Seleção de projeto** com entrada de caminho e botão de procurar
- **Métricas em tempo real**: arquivos, diretórios, tamanho total e extensões únicas
- **Barra de progresso** animada durante a análise
- **3 abas de visualização**:
  - 🌳 **Árvore**: estrutura do projeto em formato tree
  - 📊 **Estatísticas**: distribuição por extensão com tamanhos
  - 📄 **JSON**: exportação completa dos dados
- **Log de execução** com timestamps
- **Estados visuais**: pronto, analisando, concluído, falha

## Servidor MCP

O módulo `devagent.mcp_server` expõe `escanear_projeto` e `obter_arvore_projeto` através de um servidor chamado `DevAgentMCPServer`:

```bash
python -m devagent.mcp_server
```

## Segurança

A varredura aplica exclusões de segurança padrão (`.env`, `.git`, `__pycache__`, `venv`, etc.) e, quando presente, as regras de `.gitignore` da raiz analisada. Links simbólicos não são seguidos para evitar fuga do diretório.

## API Python

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
