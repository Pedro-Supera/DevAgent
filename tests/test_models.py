"""Testes unitários para os modelos do DevAgent."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from devagent.models import ItemEstrutura, ResultadoScanner


def test_item_rejeita_tamanho_negativo() -> None:
    with pytest.raises(ValueError, match="não pode ser negativo"):
        ItemEstrutura(Path("app.py"), False, -1, ".py")


def test_item_rejeita_tipos_incompativeis() -> None:
    with pytest.raises(TypeError, match="caminho_relativo deve ser um pathlib.Path"):
        ItemEstrutura("app.py", False, 1, ".py")

    with pytest.raises(TypeError, match="eh_diretorio deve ser bool"):
        ItemEstrutura(Path("app.py"), "sim", 1, ".py")

    with pytest.raises(TypeError, match="tamanho_bytes deve ser int"):
        ItemEstrutura(Path("app.py"), False, 1.5, ".py")

    with pytest.raises(TypeError, match="extensao deve ser str"):
        ItemEstrutura(Path("app.py"), False, 1, 123)


def test_item_booleans_sao_rejeitados() -> None:
    with pytest.raises(TypeError, match="tamanho_bytes deve ser int"):
        ItemEstrutura(Path("app.py"), False, True, ".py")


def test_item_eh_imutavel() -> None:
    item = ItemEstrutura(Path("app.py"), False, 10, ".py")
    with pytest.raises(FrozenInstanceError):
        item.tamanho_bytes = 20


def test_resultado_rejeita_itens_invalidos() -> None:
    with pytest.raises(TypeError, match="itens deve conter apenas ItemEstrutura"):
        ResultadoScanner(Path("."), ["não é item"], 0, 0)


def test_resultado_rejeita_contagem_negativa() -> None:
    with pytest.raises(ValueError, match="total_arquivos não pode ser negativo"):
        ResultadoScanner(Path("."), [], -1, 0)


def test_resultado_eh_mutavel() -> None:
    resultado = ResultadoScanner(Path("/projeto"), [], 0, 0)
    resultado.total_arquivos = 5
    assert resultado.total_arquivos == 5


def test_resultado_metricas_e_busca() -> None:
    itens = [
        ItemEstrutura(Path("a.py"), False, 10, ".py"),
        ItemEstrutura(Path("b.py"), False, 20, ".py"),
        ItemEstrutura(Path("dados"), True, 0, ""),
        ItemEstrutura(Path("README"), False, 5, ""),
    ]
    resultado = ResultadoScanner(Path("/projeto"), itens, 3, 1)

    stats = resultado.estatisticas_extensao
    assert stats[".py"]["quantidade"] == 2
    assert stats[".py"]["tamanho_total"] == 30
    assert stats[".py"]["tamanho_medio"] == 15.0

    assert resultado.tamanho_total_bytes == 35
    assert resultado.extensao_mais_comum == ".py"

    assert {i.caminho_relativo for i in resultado.buscar_por_extensao("PY")} == {
        Path("a.py"),
        Path("b.py"),
    }
    assert [i.caminho_relativo for i in resultado.buscar_por_tamanho(10)] == [
        Path("a.py"),
        Path("README"),
    ]


def test_resultado_vazio() -> None:
    resultado = ResultadoScanner(Path("/vazio"), [], 0, 0)
    assert resultado.estatisticas_extensao == {}
    assert resultado.tamanho_total_bytes == 0
    assert resultado.extensao_mais_comum == "Nenhuma"
    assert resultado.para_arvore_texto() == "vazio/"


def test_resultado_serialization_json() -> None:
    item = ItemEstrutura(Path("src/app.py"), False, 7, ".py")
    resultado = ResultadoScanner(Path("/projeto"), [item], 1, 0)
    import json

    dados = json.loads(resultado.para_json())
    assert dados["raiz"] == "/projeto"
    assert dados["total_arquivos"] == 1
    assert dados["itens"][0]["caminho_relativo"] == "src/app.py"
    assert dados["estatisticas_extensao"][".py"]["quantidade"] == 1
    assert dados["tamanho_total_bytes"] == 7
