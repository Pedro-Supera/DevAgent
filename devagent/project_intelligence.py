"""Leitura controlada e inteligência agregada sobre projetos."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .ast_analyzer import analisar_codigo
from .exceptions import ArquivoBinarioError, ArquivoMuitoGrandeError, ArquivoNaoPermitidoError
from .models import ItemEstrutura
from .scanner import ProjectScanner


MAX_TAMANHO_ARQUIVO_PADRAO = 100_000


@dataclass(frozen=True)
class ArquivoLido:
    """Representa o conteúdo de um arquivo aceito pela leitura controlada."""

    caminho_relativo: Path
    conteudo: str
    tamanho_bytes: int


@dataclass(frozen=True)
class ResultadoProjeto:
    """Métricas estruturais agregadas de um projeto Python."""

    raiz: Path
    total_arquivos: int
    total_diretorios: int
    arquivos_python: int
    imports: int
    classes: int
    funcoes: int
    metodos: int
    chamadas: int
    arquivos_com_erro_sintaxe: list[Path]
    arquivos_com_erro_leitura: list[Path]


class ProjectFileReader:
    """Lista e lê arquivos de uma raiz usando limites e regras determinísticas."""

    def __init__(self, root_path: Path, max_bytes: int = MAX_TAMANHO_ARQUIVO_PADRAO) -> None:
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool):
            raise TypeError("max_bytes deve ser int")
        if max_bytes <= 0:
            raise ValueError("max_bytes deve ser maior que zero")
        self.scanner = ProjectScanner(root_path)
        self.root_path = self.scanner.root_path
        self.max_bytes = max_bytes

    def listar_arquivos(self) -> list[ItemEstrutura]:
        """Retorna arquivos permitidos com caminhos relativos estáveis."""
        resultado = self.scanner.escanear()
        arquivos: list[ItemEstrutura] = []
        for item in resultado.itens:
            if item.eh_diretorio:
                continue
            caminho = self.root_path / item.caminho_relativo
            try:
                if caminho.is_symlink():
                    continue
            except OSError:
                continue
            arquivos.append(item)
        return arquivos

    def ler_arquivo(self, caminho_relativo: str | Path) -> ArquivoLido:
        """Lê um arquivo relativo à raiz sem executar ou interpretar seu conteúdo."""
        relativo = self._validar_caminho_relativo(caminho_relativo)
        caminho = (self.root_path / relativo).resolve(strict=True)

        if self.root_path not in (caminho, *caminho.parents):
            raise ArquivoNaoPermitidoError("Caminho fora da raiz do projeto")

        original = self.root_path / relativo
        if original.is_symlink():
            raise ArquivoNaoPermitidoError("Links simbólicos não são aceitos para leitura")

        if not caminho.is_file():
            raise ArquivoNaoPermitidoError("O caminho não é um arquivo regular")

        # O scanner é a fonte da política de exclusão: arquivos sensíveis,
        # caches e entradas do .gitignore não podem ser lidos por esta API.
        permitidos = {item.caminho_relativo for item in self.listar_arquivos()}
        if relativo not in permitidos:
            raise ArquivoNaoPermitidoError("Arquivo excluído pela política do projeto")

        try:
            tamanho = caminho.stat().st_size
        except OSError as erro:
            raise ArquivoNaoPermitidoError("Não foi possível obter o tamanho do arquivo") from erro

        if tamanho > self.max_bytes:
            raise ArquivoMuitoGrandeError(
                f"Arquivo excede o limite de {self.max_bytes} bytes"
            )

        try:
            dados = caminho.read_bytes()
        except OSError as erro:
            raise ArquivoNaoPermitidoError("Não foi possível ler o arquivo") from erro

        # Evita carregar um arquivo que cresceu depois do stat inicial.
        if len(dados) > self.max_bytes:
            raise ArquivoMuitoGrandeError(
                f"Arquivo excede o limite de {self.max_bytes} bytes"
            )

        if b"\x00" in dados:
            raise ArquivoBinarioError("Conteúdo binário não é aceito")

        try:
            conteudo = dados.decode("utf-8")
        except UnicodeDecodeError as erro:
            raise ArquivoBinarioError("Arquivo não é UTF-8 válido") from erro

        return ArquivoLido(
            caminho_relativo=relativo,
            conteudo=conteudo,
            tamanho_bytes=len(dados),
        )

    @staticmethod
    def _validar_caminho_relativo(caminho: str | Path) -> Path:
        if not isinstance(caminho, (str, Path)):
            raise TypeError("caminho_relativo deve ser str ou pathlib.Path")

        relativo = Path(caminho)
        if relativo.is_absolute():
            raise ArquivoNaoPermitidoError("A leitura aceita somente caminhos relativos")

        if not relativo.parts or any(parte in ("", "..") for parte in relativo.parts):
            raise ArquivoNaoPermitidoError("Caminho relativo inválido")

        if any(parte == "." for parte in relativo.parts):
            raise ArquivoNaoPermitidoError("Caminho relativo não pode conter '.'")

        return relativo


def listar_arquivos(root_path: Path) -> list[ItemEstrutura]:
    """Lista os arquivos legíveis de um projeto."""
    return ProjectFileReader(root_path).listar_arquivos()


def ler_arquivo(
    root_path: Path,
    caminho_relativo: str | Path,
    *,
    max_bytes: int = MAX_TAMANHO_ARQUIVO_PADRAO,
) -> ArquivoLido:
    """Lê um arquivo de texto UTF-8 dentro da raiz do projeto."""
    return ProjectFileReader(root_path, max_bytes=max_bytes).ler_arquivo(caminho_relativo)


def analisar_projeto(
    root_path: Path,
    *,
    max_bytes: int = MAX_TAMANHO_ARQUIVO_PADRAO,
) -> ResultadoProjeto:
    """Agrega métricas AST dos arquivos Python que puderem ser lidos."""
    leitor = ProjectFileReader(root_path, max_bytes=max_bytes)
    resultado_scanner = leitor.scanner.escanear()

    imports = classes = funcoes = metodos = chamadas = 0
    arquivos_python = 0
    erros_sintaxe: list[Path] = []
    erros_leitura: list[Path] = []

    for item in leitor.listar_arquivos():
        if item.extensao.lower() != ".py":
            continue

        arquivos_python += 1
        try:
            arquivo = leitor.ler_arquivo(item.caminho_relativo)
        except ArquivoNaoPermitidoError:
            erros_leitura.append(item.caminho_relativo)
            continue

        ast_resultado = analisar_codigo(
            arquivo.conteudo,
            leitor.root_path / arquivo.caminho_relativo,
        )
        if ast_resultado.erro is not None:
            erros_sintaxe.append(item.caminho_relativo)
            continue

        imports += len(ast_resultado.imports)
        classes += len(ast_resultado.classes)
        funcoes += len(ast_resultado.funcoes)
        metodos += sum(len(classe.metodos) for classe in ast_resultado.classes)
        chamadas += len(ast_resultado.chamadas)

    return ResultadoProjeto(
        raiz=leitor.root_path,
        total_arquivos=resultado_scanner.total_arquivos,
        total_diretorios=resultado_scanner.total_diretorios,
        arquivos_python=arquivos_python,
        imports=imports,
        classes=classes,
        funcoes=funcoes,
        metodos=metodos,
        chamadas=chamadas,
        arquivos_com_erro_sintaxe=erros_sintaxe,
        arquivos_com_erro_leitura=erros_leitura,
    )
