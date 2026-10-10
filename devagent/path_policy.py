"""Política de acesso a caminhos usados pelas ferramentas MCP."""

from __future__ import annotations

import os
from pathlib import Path

from .exceptions import CaminhoInvalidoError, CaminhoNaoPermitidoError

VARIAVEL_RAIZES_PERMITIDAS = "DEVAGENT_ALLOWED_ROOTS"


def validar_caminho(
    caminho: str | Path,
    *,
    deve_ser_diretorio: bool,
) -> Path:
    """Resolve e valida um caminho dentro das raízes permitidas.

    As raízes são lidas de ``DEVAGENT_ALLOWED_ROOTS`` separadas por
    ``os.pathsep``. Quando a variável não está definida, a raiz é o diretório
    de trabalho atual do processo MCP.
    """
    alvo = _resolver_existente(caminho, "Caminho inexistente")
    raizes = _obter_raizes_permitidas()
    if not any(_esta_dentro_de(alvo, raiz) for raiz in raizes):
        raise CaminhoNaoPermitidoError("Caminho fora das raízes permitidas")
    if deve_ser_diretorio and not alvo.is_dir():
        raise CaminhoInvalidoError(f"O caminho não é um diretório: {alvo}")
    if not deve_ser_diretorio and not alvo.is_file():
        raise CaminhoInvalidoError(f"O caminho não é um arquivo: {alvo}")
    return alvo


def caminho_relativo_permitido(caminho: str | Path) -> str:
    """Retorna um caminho relativo à raiz permitida mais específica."""
    alvo = _resolver_existente(caminho, "Caminho inexistente")
    raizes = [
        raiz for raiz in _obter_raizes_permitidas()
        if _esta_dentro_de(alvo, raiz)
    ]
    if not raizes:
        raise CaminhoNaoPermitidoError("Caminho fora das raízes permitidas")
    raiz = max(raizes, key=lambda item: len(item.parts))
    relativo = alvo.relative_to(raiz)
    return relativo.as_posix() or "."


def _obter_raizes_permitidas() -> tuple[Path, ...]:
    configuracao = os.environ.get(VARIAVEL_RAIZES_PERMITIDAS)
    valores = [os.getcwd()] if configuracao is None else configuracao.split(os.pathsep)
    if any(not valor.strip() for valor in valores):
        raise CaminhoInvalidoError("A configuração de raízes permitidas contém um caminho vazio")
    raizes: list[Path] = []
    for valor in valores:
        raiz = _resolver_existente(valor, "Raiz permitida inexistente")
        if not raiz.is_dir():
            raise CaminhoInvalidoError(f"A raiz permitida não é um diretório: {raiz}")
        raizes.append(raiz)
    if not raizes:
        raise CaminhoInvalidoError("Nenhuma raiz permitida foi configurada")
    return tuple(raizes)


def _resolver_existente(caminho: str | Path, prefixo: str) -> Path:
    try:
        resolvido = Path(caminho).expanduser().resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as erro:
        raise CaminhoInvalidoError(f"{prefixo}: {caminho}") from erro
    return resolvido


def _esta_dentro_de(caminho: Path, raiz: Path) -> bool:
    return caminho == raiz or raiz in caminho.parents