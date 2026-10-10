"""Servidor MCP reutilizável para análise de projetos."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from .ast_analyzer import analisar_arquivo
from .path_policy import caminho_relativo_permitido, validar_caminho
from .project_intelligence import (
    analisar_projeto as _analisar_projeto,
    ler_arquivo as _ler_arquivo,
    listar_arquivos as _listar_arquivos,
)
from .scanner import ProjectScanner
from .models import ASTClass, ASTFunction, ResultadoAST

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
    raiz = validar_caminho(caminho, deve_ser_diretorio=True)
    resultado = ProjectScanner(raiz).escanear()
    return {
        "raiz": caminho_relativo_permitido(resultado.raiz),
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
    raiz = validar_caminho(caminho, deve_ser_diretorio=True)
    return ProjectScanner(raiz).escanear().para_arvore_texto()


def _funcao_para_dict(funcao: ASTFunction) -> dict[str, Any]:
    """Converte uma função AST para uma estrutura serializável."""
    return {
        "nome": funcao.nome,
        "linha": funcao.linha,
        "decorators": funcao.decorators,
        "eh_metodo": funcao.eh_metodo,
    }


def _classe_para_dict(classe: ASTClass) -> dict[str, Any]:
    """Converte uma classe AST e seus métodos para uma estrutura serializável."""
    return {
        "nome": classe.nome,
        "linha": classe.linha,
        "decorators": classe.decorators,
        "bases": classe.bases,
        "metodos": [_funcao_para_dict(metodo) for metodo in classe.metodos],
    }


def _resultado_ast_para_dict(resultado: ResultadoAST) -> dict[str, Any]:
    """Converte um resultado AST no contrato público da ferramenta MCP."""
    return {
        "caminho": str(resultado.caminho),
        "imports": [
            {
                "modulo": item.modulo,
                "nomes": item.nomes,
                "import_relativo": item.import_relativo,
            }
            for item in resultado.imports
        ],
        "classes": [_classe_para_dict(classe) for classe in resultado.classes],
        "funcoes": [_funcao_para_dict(funcao) for funcao in resultado.funcoes],
        "chamadas": [
            {"nome": chamada.nome, "linha": chamada.linha}
            for chamada in resultado.chamadas
        ],
        "erro": resultado.erro,
        "linha_erro": resultado.linha_erro,
        "coluna_erro": resultado.coluna_erro,
    }


@mcp.tool()
def analisar_arquivo_python(caminho: str) -> dict[str, Any]:
    """Analisa estruturalmente um arquivo Python sem executá-lo."""
    arquivo = validar_caminho(caminho, deve_ser_diretorio=False)
    resultado = analisar_arquivo(arquivo)
    resposta = _resultado_ast_para_dict(resultado)
    resposta["caminho"] = caminho_relativo_permitido(arquivo)
    return resposta


@mcp.tool()
def listar_arquivos(caminho_projeto: str) -> dict[str, Any]:
    """Lista arquivos permitidos do projeto usando caminhos relativos."""
    arquivos = _listar_arquivos(caminho_projeto)
    return {
        "arquivos": [
            {
                "caminho_relativo": item.caminho_relativo.as_posix(),
                "tamanho_bytes": item.tamanho_bytes,
                "extensao": item.extensao,
            }
            for item in arquivos
        ],
        "total_arquivos": len(arquivos),
    }


@mcp.tool()
def ler_arquivo(
    caminho_projeto: str,
    caminho_relativo: str,
    limite_bytes: int = 1_048_576,
) -> dict[str, Any]:
    """Lê um arquivo UTF-8 do projeto respeitando a política de caminhos."""
    resultado = _ler_arquivo(
        caminho_projeto,
        caminho_relativo,
        limite_bytes=limite_bytes,
    )
    return {
        "caminho": resultado.caminho_relativo.as_posix(),
        "conteudo": resultado.conteudo,
        "tamanho_bytes": resultado.tamanho_bytes,
    }


@mcp.tool()
def analisar_projeto(caminho_projeto: str) -> dict[str, Any]:
    """Agrega métricas AST dos arquivos Python do projeto sem executá-los."""
    return _analisar_projeto(caminho_projeto).para_dict()


def iniciar_servidor() -> None:
    """Inicia o transporte padrão do servidor MCP.

    Raises:
        RuntimeError: Se o transporte MCP não puder ser iniciado.
    """
    mcp.run()


if __name__ == "__main__":
    iniciar_servidor()
