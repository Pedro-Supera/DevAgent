"""Varredura segura de projetos Python com regras de exclusão."""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Iterator

import pathspec

from .exceptions import CaminhoInvalidoError, ErroVarreduraError
from .models import ItemEstrutura, ResultadoScanner


DIRETORIOS_IGNORADOS = {
    ".git",
    ".ssh",
    ".aws",
    ".kube",
    ".azure",
    "__pycache__",
    ".venv",
    "venv",
    ".pytest_cache",
    ".egg-info",
    "build",
    "dist",
    ".idea",
    ".vscode",
}
PADROES_ARQUIVOS_IGNORADOS = (
    ".env",
    ".env.*",
    "*.env",
    ".envrc",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "*.pyc",
    "*.pyo",
    "*.log",
    ".DS_Store",
    "*.key",
    "*.pem",
    "*.p12",
    "*.pfx",
    "*.jks",
    "*.keystore",
    "*.secret",
    "*.secrets",
    "*.token",
    "*.tfstate",
    "*.tfstate.*",
    "credentials",
    "credentials.*",
    "service-account*.json",
    "id_rsa",
    "id_rsa.*",
    "id_ed25519",
    "id_ed25519.*",
)
MAX_ENTRADAS_VARREDURA = 50_000


class ProjectScanner:
    """Percorre uma raiz sem permitir traversal por links simbólicos.

    Args:
        root_path: Diretório que será usado como raiz da análise.

    Raises:
        CaminhoInvalidoError: Se a raiz não existir, não for diretório ou não
            puder ser resolvida.
    """

    def __init__(self, root_path: Path) -> None:
        """Inicializa o scanner e valida a raiz da análise.

        Args:
            root_path: Diretório que será analisado.

        Raises:
            CaminhoInvalidoError: Se `root_path` não existir, não for diretório
                ou não puder ser resolvido.
            TypeError: Se `root_path` não for um caminho aceito pelo pathlib.
        """
        try:
            self.root_path = Path(root_path).expanduser().resolve()
            if not self.root_path.exists():
                raise CaminhoInvalidoError(f"Diretório inexistente: {self.root_path}")
            if not self.root_path.is_dir():
                raise CaminhoInvalidoError(f"O caminho não é um diretório: {self.root_path}")
        except CaminhoInvalidoError:
            raise
        except (OSError, RuntimeError) as erro:
            raise CaminhoInvalidoError(f"Não foi possível resolver a raiz: {root_path}") from erro
        self._gitignore = self._carregar_gitignore()
        self._entradas_visitadas = 0

    def escanear(self) -> ResultadoScanner:
        """Executa a varredura e ignora entradas inacessíveis.

        Returns:
            Resultado imutável com os arquivos e diretórios encontrados.

        Raises:
            ErroVarreduraError: Se ocorrer uma falha inesperada ao percorrer a
            raiz ou se a varredura exceder o limite de entradas. Erros de
            permissão, arquivos removidos e symlinks externos são ignorados.
        """
        self._entradas_visitadas = 0
        try:
            itens = list(self._visitar(self.root_path))
        except (PermissionError, FileNotFoundError):
            itens = []
        except OSError as erro:
            raise ErroVarreduraError(f"Falha ao varrer {self.root_path}") from erro
        return ResultadoScanner(
            raiz=self.root_path,
            itens=itens,
            total_arquivos=sum(not item.eh_diretorio for item in itens),
            total_diretorios=sum(item.eh_diretorio for item in itens),
        )

    def _visitar(self, diretorio: Path) -> Iterator[ItemEstrutura]:
        """Percorre a árvore em profundidade sem recursão Python.

        Args:
            diretorio: Diretório resolvido que será visitado.

        Yields:
            Itens acessíveis encontrados no diretório.
        """
        entradas = self._ler_entradas_ordenadas(diretorio)
        if entradas is None:
            return
        pilha: list[Iterator[os.DirEntry[str]]] = [iter(entradas)]

        while pilha:
            try:
                entrada = next(pilha[-1])
            except StopIteration:
                pilha.pop()
                continue
            caminho = Path(entrada.path)
            try:
                if entrada.is_symlink():
                    destino = caminho.resolve(strict=True)
                    if self.root_path not in (destino, *destino.parents):
                        continue
                relativo = caminho.relative_to(self.root_path)
                eh_diretorio = entrada.is_dir(follow_symlinks=False)
            except (PermissionError, FileNotFoundError, OSError, RuntimeError, ValueError):
                continue
            if self._deve_ignorar(relativo, eh_diretorio):
                continue
            try:
                if entrada.is_symlink():
                    eh_diretorio = False
                tamanho = 0 if eh_diretorio else entrada.stat(follow_symlinks=False).st_size
            except (PermissionError, FileNotFoundError, OSError):
                continue

            item = ItemEstrutura(
                caminho_relativo=relativo,
                eh_diretorio=eh_diretorio,
                tamanho_bytes=tamanho,
                extensao="" if eh_diretorio else caminho.suffix,
            )
            yield item
            if eh_diretorio:
                entradas_filhas = self._ler_entradas_ordenadas(caminho)
                if entradas_filhas is not None:
                    pilha.append(iter(entradas_filhas))

    def _ler_entradas_ordenadas(
        self,
        diretorio: Path,
    ) -> list[os.DirEntry[str]] | None:
        try:
            with os.scandir(diretorio) as iterator:
                entradas: list[os.DirEntry[str]] = []
                for entrada in iterator:
                    self._entradas_visitadas += 1
                    if self._entradas_visitadas > MAX_ENTRADAS_VARREDURA:
                        raise ErroVarreduraError(
                            f"Varredura excedeu o limite de {MAX_ENTRADAS_VARREDURA} entradas"
                        )
                    entradas.append(entrada)
        except (PermissionError, FileNotFoundError, OSError):
            return None
        return sorted(entradas, key=lambda entrada: entrada.name.lower())

    def _deve_ignorar(self, relativo: Path, eh_diretorio: bool) -> bool:
        """Aplica as regras de exclusão a uma entrada.

        Args:
            relativo: Caminho da entrada relativo à raiz.
            eh_diretorio: Indica se a entrada é um diretório.

        Returns:
            `True` quando a entrada deve ser omitida da análise.
        """
        partes = relativo.parts
        if eh_diretorio and any(parte in DIRETORIOS_IGNORADOS or parte.endswith(".egg-info") for parte in partes):
            return True
        if not eh_diretorio and any(fnmatch.fnmatch(relativo.name, padrao) for padrao in PADROES_ARQUIVOS_IGNORADOS):
            return True
        if self._gitignore and self._gitignore.match_file(relativo.as_posix()):
            return True
        return False

    def _carregar_gitignore(self) -> pathspec.PathSpec | None:
        """Carrega o `.gitignore` da raiz, quando estiver disponível.

        Returns:
            Especificação do Git ignore ou `None` quando o arquivo não puder ser lido.
        """
        arquivo = self.root_path / ".gitignore"
        try:
            conteudo = arquivo.read_text(encoding="utf-8")
        except (FileNotFoundError, PermissionError, OSError):
            return None
        return pathspec.PathSpec.from_lines("gitignore", conteudo.splitlines())


def escanear_projeto(root_path: Path) -> ResultadoScanner:
    """Executa uma varredura usando a API funcional do módulo.

    Args:
        root_path: Diretório que será analisado.

    Returns:
        Resultado da varredura.

    Raises:
        CaminhoInvalidoError: Se `root_path` não for uma raiz válida.
        ErroVarreduraError: Se ocorrer uma falha inesperada na varredura.
    """
    return ProjectScanner(root_path).escanear()
