"""Testes do analisador estrutural baseado em AST."""

import ast
from pathlib import Path

import pytest

from devagent import ast_analyzer
from devagent.ast_analyzer import MAX_TAMANHO_ARQUIVO_AST_BYTES, analisar_arquivo, analisar_codigo


def test_arquivo_vazio(tmp_path: Path) -> None:
    arquivo = tmp_path / "vazio.py"
    arquivo.write_text("", encoding="utf-8")

    resultado = analisar_arquivo(arquivo)

    assert resultado.erro is None
    assert resultado.imports == []
    assert resultado.classes == []
    assert resultado.funcoes == []
    assert resultado.chamadas == []


def test_arquivo_acima_do_limite_nao_e_analisado(tmp_path: Path) -> None:
    arquivo = tmp_path / "grande.py"
    arquivo.write_bytes(b"x" * (MAX_TAMANHO_ARQUIVO_AST_BYTES + 1))

    resultado = analisar_arquivo(arquivo)

    assert resultado.erro == f"Arquivo excede o limite de {MAX_TAMANHO_ARQUIVO_AST_BYTES} bytes."
    assert resultado.funcoes == []
    assert resultado.chamadas == []


def test_arquivo_com_encoding_invalido_retorna_erro_controlado(tmp_path: Path) -> None:
    arquivo = tmp_path / "encoding.py"
    arquivo.write_bytes(b"valor = '\xff'")

    resultado = analisar_arquivo(arquivo)

    assert resultado.erro == "Arquivo não está codificado em UTF-8."
    assert resultado.imports == []


def test_recursao_excessiva_retorna_erro_controlado(monkeypatch: pytest.MonkeyPatch) -> None:
    def exceder_recursao(self: ast_analyzer._Visitor, arvore: ast.AST) -> None:
        assert isinstance(self, ast_analyzer._Visitor)
        assert isinstance(arvore, ast.Module)
        raise RecursionError

    monkeypatch.setattr(ast_analyzer._Visitor, "visit", exceder_recursao)

    resultado = analisar_codigo("valor = 1")

    assert resultado.erro == "Análise excedeu o limite de recursão."
    assert resultado.funcoes == []


def test_import_simples() -> None:
    resultado = analisar_codigo("import os")

    assert [(item.modulo, item.nomes) for item in resultado.imports] == [("os", [])]


def test_import_from() -> None:
    resultado = analisar_codigo("from pathlib import Path")

    assert resultado.imports[0].modulo == "pathlib"
    assert resultado.imports[0].nomes == ["Path"]


def test_funcao() -> None:
    resultado = analisar_codigo("def somar(a, b):\n    return a + b\n")

    assert [(item.nome, item.linha, item.eh_metodo) for item in resultado.funcoes] == [("somar", 1, False)]


def test_classe_e_metodos() -> None:
    resultado = analisar_codigo("class Pessoa:\n    def falar(self):\n        return 'oi'\n")

    assert resultado.classes[0].nome == "Pessoa"
    assert [(item.nome, item.eh_metodo) for item in resultado.classes[0].metodos] == [("falar", True)]


def test_decorators() -> None:
    resultado = analisar_codigo("@decorador\nclass A:\n    @property\n    def valor(self):\n        return 1\n")

    assert resultado.classes[0].decorators == ["decorador"]
    assert resultado.classes[0].metodos[0].decorators == ["property"]


def test_chamadas_de_funcao_e_metodo() -> None:
    resultado = analisar_codigo("print('oi')\nobj.salvar()\n")

    assert [(item.nome, item.linha) for item in resultado.chamadas] == [("print", 1), ("obj.salvar", 2)]


def test_multiplos_elementos_no_mesmo_arquivo() -> None:
    resultado = analisar_codigo("import os\nfrom sys import path\ndef f():\n    os.getcwd()\nclass A:\n    def m(self):\n        f()\n")

    assert len(resultado.imports) == 2
    assert [item.nome for item in resultado.funcoes] == ["f", "m"]
    assert resultado.classes[0].metodos[0].nome == "m"
    assert [item.nome for item in resultado.chamadas] == ["os.getcwd", "f"]


def test_erro_de_sintaxe_retorna_resultado_controlado() -> None:
    resultado = analisar_codigo("def quebrada(:\n", Path("quebrada.py"))

    assert resultado.erro
    assert resultado.linha_erro == 1
    assert resultado.caminho == Path("quebrada.py")
    assert resultado.imports == []


def test_codigo_analisado_nao_e_executado(tmp_path: Path) -> None:
    marcador = tmp_path / "executado.txt"
    arquivo = tmp_path / "perigoso.py"
    arquivo.write_text(
        f"from pathlib import Path\nPath({str(marcador)!r}).write_text('executado')\n",
        encoding="utf-8",
    )

    resultado = analisar_arquivo(arquivo)

    assert resultado.erro is None
    assert not marcador.exists()
    assert [item.nome for item in resultado.chamadas] == ["Path.write_text", "Path"]