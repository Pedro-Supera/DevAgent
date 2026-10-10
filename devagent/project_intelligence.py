"""Operações de leitura controlada para inteligência de projetos."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .exceptions import CaminhoInvalidoError, CaminhoNaoPermitidoError
from .models import ItemEstrutura
from .path_policy import validar_caminho
from .scanner import ProjectScanner

MAX_TAMANHO_ARQUIVO_LEITURA_BYTES = 1_048_576


@dataclass(frozen=True)
class ConteudoArquivo:
    """Conteúdo UTF-8 de um arquivo permitido no projeto."""

    caminho_relativo: Path
    conteudo: str
    tamanho_bytes: int


def listar_arquivos(caminho_projeto: str | Path) -> list[ItemEstrutura]:
    """Lista apenas arquivos visíveis ao scanner, com caminhos relativos."""
    raiz = validar_caminho(caminho_projeto, deve_ser_diretorio=True)
    resultado = ProjectScanner(raiz).escanear()
    return [item for item in resultado.itens if not item.eh_diretorio]


def ler_arquivo(
    caminho_projeto: str | Path,
    caminho_relativo: str | Path,
    *,
    limite_bytes: int = MAX_TAMANHO_ARQUIVO_LEITURA_BYTES,
) -> ConteudoArquivo:
    """Lê um arquivo UTF-8 dentro do projeto, sem seguir caminhos externos."""
    raiz = validar_caminho(caminho_projeto, deve_ser_diretorio=True)
    relativo = Path(caminho_relativo)
    if (
        not str(caminho_relativo)
        or relativo.is_absolute()
        or ".." in relativo.parts
        or relativo == Path(".")
    ):
        raise CaminhoInvalidoError("O caminho do arquivo deve ser relativo ao projeto")
    if (
        not isinstance(limite_bytes, int)
        or isinstance(limite_bytes, bool)
        or limite_bytes < 1
        or limite_bytes > MAX_TAMANHO_ARQUIVO_LEITURA_BYTES
    ):
        raise CaminhoInvalidoError(
            f"O limite deve estar entre 1 e {MAX_TAMANHO_ARQUIVO_LEITURA_BYTES} bytes"
        )

    try:
        arquivo = validar_caminho(raiz / relativo, deve_ser_diretorio=False)
    except CaminhoNaoPermitidoError as erro:
        raise CaminhoNaoPermitidoError(
            "O arquivo está fora das raízes permitidas"
        ) from erro
    except CaminhoInvalidoError as erro:
        raise CaminhoInvalidoError(
            "O arquivo solicitado não existe ou não é um arquivo"
        ) from erro

    if raiz not in arquivo.parents:
        raise CaminhoNaoPermitidoError("O arquivo está fora da raiz do projeto")

    scanner = ProjectScanner(raiz)
    caminho_resolvido_relativo = arquivo.relative_to(raiz)
    if scanner.caminho_ignorado(relativo) or scanner.caminho_ignorado(
        caminho_resolvido_relativo
    ):
        raise CaminhoNaoPermitidoError("O arquivo está excluído da análise")

    try:
        if arquivo.stat().st_size > limite_bytes:
            raise CaminhoInvalidoError(
                f"Arquivo excede o limite de {limite_bytes} bytes"
            )
        with arquivo.open("rb") as fluxo:
            conteudo_bytes = fluxo.read(limite_bytes + 1)
    except CaminhoInvalidoError:
        raise
    except OSError as erro:
        raise CaminhoInvalidoError("Não foi possível ler o arquivo") from erro

    if len(conteudo_bytes) > limite_bytes:
        raise CaminhoInvalidoError(f"Arquivo excede o limite de {limite_bytes} bytes")
    if b"\x00" in conteudo_bytes:
        raise CaminhoInvalidoError("Arquivo binário não pode ser lido")
    try:
        conteudo = conteudo_bytes.decode("utf-8")
    except UnicodeDecodeError as erro:
        raise CaminhoInvalidoError("Arquivo não está codificado em UTF-8") from erro

    return ConteudoArquivo(
        caminho_relativo=relativo,
        conteudo=conteudo,
        tamanho_bytes=len(conteudo_bytes),
    )
