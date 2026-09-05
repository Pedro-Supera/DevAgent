"""Servidor MCP reutilizável para análise de projetos."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from .scanner import ProjectScanner

mcp = MCPServer("DevAgentMCPServer")


@mcp.tool()
def escanear_projeto(caminho: str) -> dict[str, Any]:
    """Escaneia um projeto e devolve seus dados estruturados.

    Args:
        caminho: Caminho da pasta raiz do projeto.

    Returns:
        Dicionário serializável com a raiz, os itens e suas contagens.

    Raises:
        CaminhoInvalidoError: Se `caminho` não for uma pasta válida.
        ErroVarreduraError: Se ocorrer uma falha inesperada na varredura.
    """
    resultado = ProjectScanner(Path(caminho)).escanear()
    return {
        "raiz": str(resultado.raiz),
        "itens": [
            {
                "caminho_relativo": str(item.caminho_relativo),
                "eh_diretorio": item.eh_diretorio,
                "tamanho_bytes": item.tamanho_bytes,
                "extensao": item.extensao,
            }
            for item in resultado.itens
        ],
        "total_arquivos": resultado.total_arquivos,
        "total_diretorios": resultado.total_diretorios,
    }


@mcp.tool()
def obter_arvore_projeto(caminho: str) -> str:
    """Escaneia um projeto e devolve sua árvore textual.

    Args:
        caminho: Caminho da pasta raiz do projeto.

    Returns:
        Árvore textual com a estrutura encontrada.

    Raises:
        CaminhoInvalidoError: Se `caminho` não for uma pasta válida.
        ErroVarreduraError: Se ocorrer uma falha inesperada na varredura.
    """
    return ProjectScanner(Path(caminho)).escanear().para_arvore_texto()


def iniciar_servidor() -> None:
    """Inicia o transporte padrão do servidor MCP.

    Raises:
        RuntimeError: Se o transporte MCP não puder ser iniciado.
    """
    mcp.run()


if __name__ == "__main__":
    iniciar_servidor()
