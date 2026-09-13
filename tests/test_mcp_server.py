"""Testes da exposição MCP do analisador AST."""

import json
from pathlib import Path

import pytest

from devagent.exceptions import CaminhoInvalidoError, CaminhoNaoPermitidoError
from devagent.mcp_server import (
    analisar_arquivo_python,
    escanear_projeto,
    obter_arvore_projeto,
)


def test_analisar_arquivo_python_retorna_contrato_completo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEVAGENT_ALLOWED_ROOTS", str(tmp_path))
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


def test_analisar_arquivo_python_retorna_erro_de_sintaxe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEVAGENT_ALLOWED_ROOTS", str(tmp_path))
    arquivo = tmp_path / "invalido.py"
    arquivo.write_text("def quebrada(:\n", encoding="utf-8")

    resultado = analisar_arquivo_python(str(arquivo))

    assert resultado["caminho"] == str(arquivo)
    assert resultado["erro"]
    assert resultado["linha_erro"] == 1
    assert resultado["coluna_erro"] is not None
    assert resultado["imports"] == []
    json.dumps(resultado)


def test_ferramentas_mcp_existentes_continuam_funcionais(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEVAGENT_ALLOWED_ROOTS", str(tmp_path))
    arquivo = tmp_path / "arquivo.py"
    arquivo.write_text("x = 1", encoding="utf-8")

    resultado_scanner = escanear_projeto(str(tmp_path))
    arvore = obter_arvore_projeto(str(tmp_path))

    assert resultado_scanner["total_arquivos"] == 1
    assert resultado_scanner["itens"][0]["caminho_relativo"] == "arquivo.py"
    assert "arquivo.py" in arvore


def test_mcp_rejeita_caminho_fora_da_raiz_permitida(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    permitida = tmp_path / "permitida"
    externa = tmp_path / "externa"
    permitida.mkdir()
    externa.mkdir()
    arquivo = externa / "segredo.py"
    arquivo.write_text("segredo = True", encoding="utf-8")
    monkeypatch.setenv("DEVAGENT_ALLOWED_ROOTS", str(permitida))

    with pytest.raises(CaminhoNaoPermitidoError):
        analisar_arquivo_python(str(arquivo))


def test_mcp_rejeita_traversal_e_symlink_externo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    permitida = tmp_path / "permitida"
    externa = tmp_path / "externa"
    permitida.mkdir()
    externa.mkdir()
    arquivo = externa / "segredo.py"
    arquivo.write_text("segredo = True", encoding="utf-8")
    (permitida / "atalho.py").symlink_to(arquivo)
    monkeypatch.setenv("DEVAGENT_ALLOWED_ROOTS", str(permitida))

    with pytest.raises(CaminhoNaoPermitidoError):
        analisar_arquivo_python(str(permitida / ".." / "externa" / "segredo.py"))
    with pytest.raises(CaminhoNaoPermitidoError):
        analisar_arquivo_python(str(permitida / "atalho.py"))


def test_mcp_rejeita_caminho_inexistente_e_tipo_incorreto(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEVAGENT_ALLOWED_ROOTS", str(tmp_path))

    with pytest.raises(CaminhoInvalidoError):
        analisar_arquivo_python(str(tmp_path / "nao_existe.py"))
    with pytest.raises(CaminhoInvalidoError):
        analisar_arquivo_python(str(tmp_path))
    with pytest.raises(CaminhoInvalidoError):
        escanear_projeto(str(tmp_path / "nao_existe"))


def test_mcp_aceita_caminho_relativo_na_raiz_de_trabalho(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    arquivo = tmp_path / "relativo.py"
    arquivo.write_text("valor = 1", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEVAGENT_ALLOWED_ROOTS", raising=False)

    resultado = analisar_arquivo_python("relativo.py")

    assert resultado["caminho"] == str(arquivo.resolve())
    assert resultado["erro"] is None