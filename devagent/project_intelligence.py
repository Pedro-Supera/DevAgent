"""Operações de leitura controlada para inteligência de projetos."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .ast_analyzer import analisar_codigo
from .exceptions import CaminhoInvalidoError, CaminhoNaoPermitidoError
from .models import ItemEstrutura, ResultadoAST
from .path_policy import validar_caminho
from .scanner import ProjectScanner

MAX_TAMANHO_ARQUIVO_LEITURA_BYTES = 1_048_576


@dataclass(frozen=True)
class ConteudoArquivo:
    """Conteúdo UTF-8 de um arquivo permitido no projeto."""

    caminho_relativo: Path
    conteudo: str
    tamanho_bytes: int


@dataclass(frozen=True)
class ErroAnaliseArquivo:
    """Falha de leitura ou análise identificada para um arquivo do projeto."""

    caminho_relativo: Path
    erro: str
    linha: int | None = None
    coluna: int | None = None


@dataclass(frozen=True)
class ResultadoAnaliseProjeto:
    """Métricas agregadas da análise estática dos arquivos Python do projeto."""

    total_arquivos_python: int
    total_imports: int
    total_classes: int
    total_funcoes: int
    total_chamadas: int
    arquivos_com_erro: list[ErroAnaliseArquivo]

    def para_dict(self) -> dict[str, Any]:
        """Serializa o resultado sem expor caminhos absolutos."""
        return {
            "total_arquivos_python": self.total_arquivos_python,
            "total_imports": self.total_imports,
            "total_classes": self.total_classes,
            "total_funcoes": self.total_funcoes,
            "total_chamadas": self.total_chamadas,
            "arquivos_com_erro": [
                {
                    "caminho": str(item.caminho_relativo),
                    "erro": item.erro,
                    "linha": item.linha,
                    "coluna": item.coluna,
                }
                for item in self.arquivos_com_erro
            ],
        }


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
    scanner = ProjectScanner(raiz)
    return _ler_arquivo_na_raiz(
        raiz,
        caminho_relativo,
        limite_bytes=limite_bytes,
        scanner=scanner,
    )


def _ler_arquivo_na_raiz(
    raiz: Path,
    caminho_relativo: str | Path,
    *,
    limite_bytes: int,
    scanner: ProjectScanner,
) -> ConteudoArquivo:
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


def analisar_projeto(caminho_projeto: str | Path) -> ResultadoAnaliseProjeto:
    """Agrega métricas AST sem executar os arquivos Python encontrados."""
    raiz = validar_caminho(caminho_projeto, deve_ser_diretorio=True)
    scanner = ProjectScanner(raiz)
    arquivos_python = [
        item for item in scanner.escanear().itens
        if not item.eh_diretorio and item.caminho_relativo.suffix == ".py"
    ]
    resultados: list[ResultadoAST] = []
    erros: list[ErroAnaliseArquivo] = []

    for item in arquivos_python:
        try:
            conteudo = _ler_arquivo_na_raiz(
                raiz,
                item.caminho_relativo,
                limite_bytes=MAX_TAMANHO_ARQUIVO_LEITURA_BYTES,
                scanner=scanner,
            )
        except CaminhoInvalidoError as erro:
            erros.append(ErroAnaliseArquivo(item.caminho_relativo, str(erro)))
            continue
        resultado = analisar_codigo(conteudo.conteudo, item.caminho_relativo)
        if resultado.erro:
            erros.append(
                ErroAnaliseArquivo(
                    caminho_relativo=item.caminho_relativo,
                    erro=resultado.erro,
                    linha=resultado.linha_erro,
                    coluna=resultado.coluna_erro,
                )
            )
        else:
            resultados.append(resultado)

    return ResultadoAnaliseProjeto(
        total_arquivos_python=len(arquivos_python),
        total_imports=sum(len(item.imports) for item in resultados),
        total_classes=sum(len(item.classes) for item in resultados),
        total_funcoes=sum(len(item.funcoes) for item in resultados),
        total_chamadas=sum(len(item.chamadas) for item in resultados),
        arquivos_com_erro=erros,
    )
