"""Servidor MCP reutilizável para análise de projetos."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from .ast_analyzer import analisar_arquivo
from .path_policy import validar_caminho
from .scanner import ProjectScanner
from .models import ASTClass, ASTFunction, ResultadoAST
from .project_intelligence import analisar_projeto, ler_arquivo, listar_arquivos

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
    return _resultado_ast_para_dict(resultado)


def _item_para_dict(item: Any) -> dict[str, Any]:
    """Converte um item de estrutura para o contrato MCP."""
    return {
        "caminho_relativo": str(item.caminho_relativo),
        "eh_diretorio": item.eh_diretorio,
        "tamanho_bytes": item.tamanho_bytes,
        "extensao": item.extensao,
    }


@mcp.tool()
def listar_arquivos_projeto(caminho: str) -> list[dict[str, Any]]:
    """Lista arquivos permitidos de um projeto usando caminhos relativos."""
    raiz = validar_caminho(caminho, deve_ser_diretorio=True)
    return [_item_para_dict(item) for item in listar_arquivos(raiz)]


@mcp.tool()
def ler_arquivo_projeto(caminho: str, arquivo: str, max_bytes: int = 100_000) -> dict[str, Any]:
    """Lê um arquivo UTF-8 relativo à raiz, com limite explícito de tamanho."""
    raiz = validar_caminho(caminho, deve_ser_diretorio=True)
    resultado = ler_arquivo(raiz, arquivo, max_bytes=max_bytes)
    return {
        "caminho_relativo": str(resultado.caminho_relativo),
        "conteudo": resultado.conteudo,
        "tamanho_bytes": resultado.tamanho_bytes,
    }


@mcp.tool()
def analisar_projeto_python(caminho: str, max_bytes: int = 100_000) -> dict[str, Any]:
    """Agrega métricas AST dos arquivos Python legíveis de um projeto."""
    raiz = validar_caminho(caminho, deve_ser_diretorio=True)
    resultado = analisar_projeto(raiz, max_bytes=max_bytes)
    return {
        "raiz": str(resultado.raiz),
        "total_arquivos": resultado.total_arquivos,
        "total_diretorios": resultado.total_diretorios,
        "arquivos_python": resultado.arquivos_python,
        "imports": resultado.imports,
        "classes": resultado.classes,
        "funcoes": resultado.funcoes,
        "metodos": resultado.metodos,
        "chamadas": resultado.chamadas,
        "arquivos_com_erro_sintaxe": [str(p) for p in resultado.arquivos_com_erro_sintaxe],
        "arquivos_com_erro_leitura": [str(p) for p in resultado.arquivos_com_erro_leitura],
    }


def iniciar_servidor() -> None:
    """Inicia o transporte padrão do servidor MCP.

    Raises:
        RuntimeError: Se o transporte MCP não puder ser iniciado.
    """
    mcp.run()


if __name__ == "__main__":
    iniciar_servidor()
