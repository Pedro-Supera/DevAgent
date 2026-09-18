"""Testes da inteligência controlada de projetos."""

from pathlib import Path

import pytest

from devagent.exceptions import (
    ArquivoBinarioError,
    ArquivoMuitoGrandeError,
    ArquivoNaoPermitidoError,
    CaminhoInvalidoError,
    CaminhoNaoPermitidoError,
)
from devagent.mcp_server import (
    analisar_projeto_python,
    ler_arquivo_projeto,
    listar_arquivos_projeto,
)
from devagent.project_intelligence import ProjectFileReader, analisar_projeto


def test_listar_arquivos_retorna_caminhos_relativos_e_respeita_exclusoes(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('ok')", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Projeto", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=nao", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("x", encoding="utf-8")

    resultado = ProjectFileReader(tmp_path).listar_arquivos()

    assert [item.caminho_relativo for item in resultado] == [
        Path("main.py"),
        Path("README.md"),
    ] or {item.caminho_relativo for item in resultado} == {
        Path("main.py"),
        Path("README.md"),
    }


def test_ler_arquivo_utf8_valido(tmp_path: Path) -> None:
    arquivo = tmp_path / "README.md"
    arquivo.write_text("Olá, DevAgent!", encoding="utf-8")

    resultado = ProjectFileReader(tmp_path).ler_arquivo("README.md")

    assert resultado.caminho_relativo == Path("README.md")
    assert resultado.conteudo == "Olá, DevAgent!"
    assert resultado.tamanho_bytes == len("Olá, DevAgent!".encode("utf-8"))


def test_ler_arquivo_rejeita_inexistente_diretorio_e_traversal(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()

    leitor = ProjectFileReader(tmp_path)

    with pytest.raises((ArquivoNaoPermitidoError, FileNotFoundError)):
        leitor.ler_arquivo("nao_existe.txt")
    with pytest.raises(ArquivoNaoPermitidoError):
        leitor.ler_arquivo("src")
    with pytest.raises(ArquivoNaoPermitidoError):
        leitor.ler_arquivo("../fora.txt")
    with pytest.raises(ArquivoNaoPermitidoError):
        leitor.ler_arquivo(tmp_path / "src")


def test_ler_arquivo_rejeita_arquivo_sensivel(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("TOKEN=segredo", encoding="utf-8")

    with pytest.raises(ArquivoNaoPermitidoError):
        ProjectFileReader(tmp_path).ler_arquivo(".env")


def test_ler_arquivo_rejeita_arquivo_acima_do_limite(tmp_path: Path) -> None:
    (tmp_path / "grande.txt").write_text("x" * 101, encoding="utf-8")

    with pytest.raises(ArquivoMuitoGrandeError):
        ProjectFileReader(tmp_path, max_bytes=100).ler_arquivo("grande.txt")


def test_ler_arquivo_rejeita_binario_e_utf8_invalido(tmp_path: Path) -> None:
    (tmp_path / "nulo.dat").write_bytes(b"abc\x00def")
    (tmp_path / "invalido.txt").write_bytes(b"\xff\xfe\xfd")

    leitor = ProjectFileReader(tmp_path)

    with pytest.raises(ArquivoBinarioError):
        leitor.ler_arquivo("nulo.dat")
    with pytest.raises(ArquivoBinarioError):
        leitor.ler_arquivo("invalido.txt")


def test_ler_arquivo_rejeita_symlink(tmp_path: Path) -> None:
    alvo = tmp_path / "alvo.txt"
    alvo.write_text("segredo", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(alvo)

    with pytest.raises(ArquivoNaoPermitidoError):
        ProjectFileReader(tmp_path).ler_arquivo("link.txt")


def test_analisar_projeto_agrega_ast_e_registra_erros(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        "import os\n"
        "class App:\n"
        "    def executar(self):\n"
        "        return os.getcwd()\n"
        "def helper():\n"
        "    App().executar()\n",
        encoding="utf-8",
    )
    (tmp_path / "quebrado.py").write_text("def quebrado(:\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Projeto", encoding="utf-8")

    resultado = analisar_projeto(tmp_path)

    assert resultado.total_arquivos == 3
    assert resultado.arquivos_python == 2
    assert resultado.imports == 1
    assert resultado.classes == 1
    assert resultado.funcoes == 2
    assert resultado.metodos == 1
    assert resultado.chamadas == 2
    assert resultado.arquivos_com_erro_sintaxe == [Path("quebrado.py")]
    assert resultado.arquivos_com_erro_leitura == []


def test_analisar_projeto_registra_python_grande_como_erro_de_leitura(tmp_path: Path) -> None:
    (tmp_path / "grande.py").write_text("x = 1\n" * 100, encoding="utf-8")

    resultado = analisar_projeto(tmp_path, max_bytes=10)

    assert resultado.arquivos_python == 1
    assert resultado.arquivos_com_erro_leitura == [Path("grande.py")]


def test_mcp_inteligencia_respeita_raiz_permitida(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEVAGENT_ALLOWED_ROOTS", str(tmp_path))
    (tmp_path / "main.py").write_text("x = 1", encoding="utf-8")

    arquivos = listar_arquivos_projeto(str(tmp_path))
    leitura = ler_arquivo_projeto(str(tmp_path), "main.py")
    analise = analisar_projeto_python(str(tmp_path))

    assert arquivos[0]["caminho_relativo"] == "main.py"
    assert leitura["conteudo"] == "x = 1"
    assert analise["arquivos_python"] == 1


def test_mcp_rejeita_raiz_fora_da_politica(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    permitida = tmp_path / "permitida"
    externa = tmp_path / "externa"
    permitida.mkdir()
    externa.mkdir()
    monkeypatch.setenv("DEVAGENT_ALLOWED_ROOTS", str(permitida))

    with pytest.raises(CaminhoNaoPermitidoError):
        listar_arquivos_projeto(str(externa))
    with pytest.raises(CaminhoNaoPermitidoError):
        ler_arquivo_projeto(str(externa), "segredo.txt")
    with pytest.raises(CaminhoNaoPermitidoError):
        analisar_projeto_python(str(externa))


def test_mcp_rejeita_arquivo_com_path_absoluto(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEVAGENT_ALLOWED_ROOTS", str(tmp_path))
    arquivo = tmp_path / "main.py"
    arquivo.write_text("x = 1", encoding="utf-8")

    with pytest.raises(ArquivoNaoPermitidoError):
        ler_arquivo_projeto(str(tmp_path), str(arquivo))


def test_mcp_converte_erro_de_leitura_para_json_serializavel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEVAGENT_ALLOWED_ROOTS", str(tmp_path))
    (tmp_path / "main.py").write_text("x = 1", encoding="utf-8")

    resultado = analisar_projeto_python(str(tmp_path), max_bytes=1)

    assert resultado["arquivos_python"] == 1
    assert resultado["arquivos_com_erro_leitura"] == ["main.py"]
