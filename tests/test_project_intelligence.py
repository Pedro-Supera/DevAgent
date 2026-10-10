"""Testes para a API de leitura controlada de projetos."""

from pathlib import Path

import pytest

from devagent.exceptions import CaminhoInvalidoError, CaminhoNaoPermitidoError
from devagent.project_intelligence import (
    MAX_TAMANHO_ARQUIVO_LEITURA_BYTES,
    analisar_projeto,
    ler_arquivo,
    listar_arquivos,
)


@pytest.fixture(autouse=True)
def project_is_allowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEVAGENT_ALLOWED_ROOTS", str(tmp_path))


def test_listar_arquivos_usa_caminhos_relativos_e_exclusoes(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("valor = 1", encoding="utf-8")
    (tmp_path / ".env").write_text("TOKEN=secreto", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("privado/\n", encoding="utf-8")
    (tmp_path / "privado").mkdir()
    (tmp_path / "privado" / "segredo.txt").write_text("segredo", encoding="utf-8")

    resultado = listar_arquivos(tmp_path)

    assert [item.caminho_relativo for item in resultado] == [
        Path(".gitignore"),
        Path("src/main.py"),
    ]


def test_ler_arquivo_retorna_conteudo_utf8_e_tamanho(tmp_path: Path) -> None:
    arquivo = tmp_path / "mensagem.txt"
    arquivo.write_text("olá", encoding="utf-8")

    resultado = ler_arquivo(tmp_path, "mensagem.txt")

    assert resultado.caminho_relativo == Path("mensagem.txt")
    assert resultado.conteudo == "olá"
    assert resultado.tamanho_bytes == len("olá".encode("utf-8"))


@pytest.mark.parametrize("caminho", ["", ".", "../fora.txt", "sub/../../fora.txt"])
def test_ler_arquivo_rejeita_caminhos_nao_relativos_ao_projeto(
    tmp_path: Path, caminho: str
) -> None:
    with pytest.raises(CaminhoInvalidoError):
        ler_arquivo(tmp_path, caminho)


def test_ler_arquivo_nao_escapa_da_raiz_do_projeto_dentro_da_allowlist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projeto = tmp_path / "projeto"
    externo = tmp_path / "externo.txt"
    projeto.mkdir()
    externo.write_text("privado", encoding="utf-8")
    monkeypatch.setenv("DEVAGENT_ALLOWED_ROOTS", str(tmp_path))

    with pytest.raises(CaminhoInvalidoError):
        ler_arquivo(projeto, "../externo.txt")


def test_ler_arquivo_rejeita_symlink_externo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projeto = tmp_path / "projeto"
    projeto.mkdir()
    externo = tmp_path / "externo.txt"
    externo.write_text("privado", encoding="utf-8")
    (projeto / "atalho.txt").symlink_to(externo)
    monkeypatch.setenv("DEVAGENT_ALLOWED_ROOTS", str(tmp_path))

    with pytest.raises(CaminhoNaoPermitidoError):
        ler_arquivo(projeto, "atalho.txt")


@pytest.mark.parametrize(
    ("nome", "conteudo", "mensagem"),
    [
        (".env", b"SECRET=value", "excluído"),
        ("binario.dat", b"\x00\x01", "binário"),
        ("encoding.txt", b"\xff", "UTF-8"),
    ],
)
def test_ler_arquivo_rejeita_arquivos_excluidos_ou_nao_textuais(
    tmp_path: Path, nome: str, conteudo: bytes, mensagem: str
) -> None:
    (tmp_path / nome).write_bytes(conteudo)

    with pytest.raises(CaminhoInvalidoError, match=mensagem):
        ler_arquivo(tmp_path, nome)


def test_ler_arquivo_rejeita_tamanho_acima_do_limite(tmp_path: Path) -> None:
    (tmp_path / "grande.txt").write_bytes(
        b"x" * (MAX_TAMANHO_ARQUIVO_LEITURA_BYTES + 1)
    )

    with pytest.raises(CaminhoInvalidoError, match="limite"):
        ler_arquivo(tmp_path, "grande.txt")


def test_ler_arquivo_nao_permite_aumentar_limite_global(tmp_path: Path) -> None:
    (tmp_path / "arquivo.txt").write_text("x", encoding="utf-8")

    with pytest.raises(CaminhoInvalidoError, match="limite"):
        ler_arquivo(
            tmp_path,
            "arquivo.txt",
            limite_bytes=MAX_TAMANHO_ARQUIVO_LEITURA_BYTES + 1,
        )


def test_analisar_projeto_agrega_ast_sem_executar_arquivos(tmp_path: Path) -> None:
    marcador = tmp_path / "executado.txt"
    (tmp_path / "main.py").write_text(
        "import os\n"
        "class Exemplo:\n"
        "    def rodar(self):\n"
        "        os.getcwd()\n"
        f"Path({str(marcador)!r}).write_text('executado')\n",
        encoding="utf-8",
    )
    (tmp_path / "invalido.py").write_text("def quebrada(:\n", encoding="utf-8")
    (tmp_path / "ignorado.txt").write_text("não é Python", encoding="utf-8")

    resultado = analisar_projeto(tmp_path)

    assert resultado.total_arquivos_python == 2
    assert resultado.total_imports == 1
    assert resultado.total_classes == 1
    assert resultado.total_funcoes == 1
    assert resultado.total_chamadas == 3
    assert [item.caminho_relativo for item in resultado.arquivos_com_erro] == [
        Path("invalido.py")
    ]
    assert not marcador.exists()
    assert resultado.para_dict()["arquivos_com_erro"][0]["caminho"] == "invalido.py"
