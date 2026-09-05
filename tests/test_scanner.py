"""Testes unitários do scanner."""

import json
from pathlib import Path

import pytest

from devagent.models import ResultadoScanner
from devagent.exceptions import CaminhoInvalidoError
from devagent.scanner import ProjectScanner


def test_varredura_basica(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('ok')", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "util.py").write_text("x = 1", encoding="utf-8")

    resultado = ProjectScanner(tmp_path).escanear()

    assert resultado.total_arquivos == 2
    assert resultado.total_diretorios == 1
    assert {item.caminho_relativo for item in resultado.itens} == {Path("main.py"), Path("src"), Path("src/util.py")}


def test_exclusao_de_arquivos_e_pastas_ignorados(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("x", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "lib.py").write_text("x", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "modulo.pyc").write_bytes(b"x")
    (tmp_path / ".env").write_text("SECRET=x", encoding="utf-8")
    (tmp_path / "credencial.key").write_text("secret", encoding="utf-8")
    (tmp_path / "ok.py").write_text("x", encoding="utf-8")

    resultado = ProjectScanner(tmp_path).escanear()
    caminhos = {item.caminho_relativo for item in resultado.itens}

    assert caminhos == {Path("ok.py")}


def test_exportacao_json_e_arvore(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("privado/\n", encoding="utf-8")
    (tmp_path / "publico.txt").write_text("conteudo", encoding="utf-8")
    (tmp_path / "privado").mkdir()
    (tmp_path / "privado" / "segredo.txt").write_text("segredo", encoding="utf-8")

    resultado = ProjectScanner(tmp_path).escanear()
    dados = json.loads(resultado.para_json())
    arvore = resultado.para_arvore_texto()

    assert dados["total_arquivos"] == 2
    assert "publico.txt" in arvore
    assert "segredo.txt" not in arvore


def test_estatisticas_extensao(tmp_path: Path) -> None:
    """Testa as estatísticas detalhadas por extensão."""
    (tmp_path / "main.py").write_text("print(1)", encoding="utf-8")
    (tmp_path / "utils.py").write_text("x=2", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Title", encoding="utf-8")
    (tmp_path / "config.json").write_text('{"a":1}', encoding="utf-8")
    (tmp_path / "data.bin").write_bytes(b"\x00\x01\x02\x03")
    (tmp_path / "sem_ext").write_text("conteudo", encoding="utf-8")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "nested.txt").write_text("nested", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("*.log\n", encoding="utf-8")
    (tmp_path / "debug.log").write_text("log", encoding="utf-8")

    resultado = ProjectScanner(tmp_path).escanear()
    stats = resultado.estatisticas_extensao

    # .log deve ser ignorado pelo .gitignore
    assert ".log" not in stats
    # .py deve ter 2 arquivos
    assert stats[".py"]["quantidade"] == 2
    assert stats[".md"]["quantidade"] == 1
    assert stats[".json"]["quantidade"] == 1
    assert stats[".bin"]["quantidade"] == 1
    assert stats[".txt"]["quantidade"] == 1
    assert stats[".py"]["tamanho_total"] > 0

    # .gitignore e sem_ext são arquivos sem extensão
    assert stats["(sem extensão)"]["quantidade"] == 2

    # Diretórios não aparecem nas estatísticas
    assert "(diretório)" not in stats

    # Ordenado por quantidade decrescente
    extensoes = list(stats.keys())
    if len(extensoes) > 1:
        assert stats[extensoes[0]]["quantidade"] >= stats[extensoes[1]]["quantidade"]


def test_tamanho_total_bytes(tmp_path: Path) -> None:
    """Testa a propriedade tamanho_total_bytes."""
    (tmp_path / "a.txt").write_text("a" * 100, encoding="utf-8")
    (tmp_path / "b.txt").write_text("b" * 200, encoding="utf-8")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "c.txt").write_text("c" * 50, encoding="utf-8")

    resultado = ProjectScanner(tmp_path).escanear()
    assert resultado.tamanho_total_bytes == 350


def test_extensao_mais_comum(tmp_path: Path) -> None:
    """Testa a propriedade extensao_mais_comum."""
    resultado_vazio = ProjectScanner(tmp_path).escanear()
    assert resultado_vazio.extensao_mais_comum == "Nenhuma"

    (tmp_path / "x.py").write_text("print(1)", encoding="utf-8")
    resultado_um = ProjectScanner(tmp_path).escanear()
    assert resultado_um.extensao_mais_comum == ".py"

    (tmp_path / "a.py").write_text("", encoding="utf-8")
    (tmp_path / "b.py").write_text("", encoding="utf-8")
    (tmp_path / "c.js").write_text("", encoding="utf-8")
    resultado_multiplo = ProjectScanner(tmp_path).escanear()
    assert resultado_multiplo.extensao_mais_comum == ".py"


def test_rejeita_raiz_invalida_com_excecao_de_dominio(tmp_path: Path) -> None:
    with pytest.raises(CaminhoInvalidoError):
        ProjectScanner(tmp_path / "nao_existe")

    arquivo = tmp_path / "arquivo.txt"
    arquivo.write_text("conteudo", encoding="utf-8")
    with pytest.raises(CaminhoInvalidoError):
        ProjectScanner(arquivo)


def test_ignora_symlink_que_escapa_da_raiz(tmp_path: Path) -> None:
    externo = tmp_path / "externo"
    externo.mkdir()
    (externo / "segredo.txt").write_text("segredo", encoding="utf-8")
    raiz = tmp_path / "projeto"
    raiz.mkdir()
    (raiz / "atalho").symlink_to(externo, target_is_directory=True)

    resultado = ProjectScanner(raiz).escanear()

    assert all(item.caminho_relativo != Path("atalho") for item in resultado.itens)
    assert all("segredo.txt" not in str(item.caminho_relativo) for item in resultado.itens)


def test_buscas_por_extensao_e_tamanho(tmp_path: Path) -> None:
    (tmp_path / "pequeno.py").write_text("x", encoding="utf-8")
    (tmp_path / "grande.py").write_text("x" * 20, encoding="utf-8")
    (tmp_path / "leia.txt").write_text("x", encoding="utf-8")

    resultado = ProjectScanner(tmp_path).escanear()

    assert {item.caminho_relativo for item in resultado.buscar_por_extensao("py")} == {
        Path("pequeno.py"), Path("grande.py")
    }
    assert [item.caminho_relativo for item in resultado.buscar_por_tamanho(1)] == [
        Path("leia.txt"), Path("pequeno.py")
    ]
