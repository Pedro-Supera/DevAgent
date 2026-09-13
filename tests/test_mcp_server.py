"""Testes da exposição MCP do analisador AST."""

import json
from pathlib import Path

from devagent.mcp_server import (
    analisar_arquivo_python,
    escanear_projeto,
    obter_arvore_projeto,
)


def test_analisar_arquivo_python_retorna_contrato_completo(tmp_path: Path) -> None:
    arquivo = tmp_path / "modulo.py"
    arquivo.write_text(
        "from .base import Base\n"
        "import os\n"
        "@decorador\n"
        "class Exemplo(Base):\n"
        "    @property\n"
        "    def valor(self):\n"
        "        return os.getcwd()\n"
        "def executar():\n"
        "    Exemplo().valor\n",
        encoding="utf-8",
    )

    resultado = analisar_arquivo_python(str(arquivo))

    assert resultado == {
        "caminho": str(arquivo),
        "imports": [
            {"modulo": "base", "nomes": ["Base"], "import_relativo": 1},
            {"modulo": "os", "nomes": [], "import_relativo": 0},
        ],
        "classes": [
            {
                "nome": "Exemplo",
                "linha": 4,
                "decorators": ["decorador"],
                "bases": ["Base"],
                "metodos": [
                    {
                        "nome": "valor",
                        "linha": 6,
                        "decorators": ["property"],
                        "eh_metodo": True,
                    }
                ],
            }
        ],
        "funcoes": [
            {
                "nome": "valor",
                "linha": 6,
                "decorators": ["property"],
                "eh_metodo": True,
            },
            {"nome": "executar", "linha": 8, "decorators": [], "eh_metodo": False},
        ],
        "chamadas": [
            {"nome": "os.getcwd", "linha": 7},
            {"nome": "Exemplo", "linha": 9},
        ],
        "erro": None,
        "linha_erro": None,
        "coluna_erro": None,
    }

    json.dumps(resultado)


def test_analisar_arquivo_python_retorna_erro_de_sintaxe(tmp_path: Path) -> None:
    arquivo = tmp_path / "invalido.py"
    arquivo.write_text("def quebrada(:\n", encoding="utf-8")

    resultado = analisar_arquivo_python(str(arquivo))

    assert resultado["caminho"] == str(arquivo)
    assert resultado["erro"]
    assert resultado["linha_erro"] == 1
    assert resultado["coluna_erro"] is not None
    assert resultado["imports"] == []
    json.dumps(resultado)


def test_ferramentas_mcp_existentes_continuam_funcionais(tmp_path: Path) -> None:
    arquivo = tmp_path / "arquivo.py"
    arquivo.write_text("x = 1", encoding="utf-8")

    resultado_scanner = escanear_projeto(str(tmp_path))
    arvore = obter_arvore_projeto(str(tmp_path))

    assert resultado_scanner["total_arquivos"] == 1
    assert resultado_scanner["itens"][0]["caminho_relativo"] == "arquivo.py"
    assert "arquivo.py" in arvore