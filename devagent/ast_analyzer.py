"""Análise estrutural estática de arquivos Python usando apenas ``ast``."""

from __future__ import annotations

import ast
from pathlib import Path

from .models import ASTCall, ASTClass, ASTFunction, ASTImport, ResultadoAST


class _Visitor(ast.NodeVisitor):
    """Extrai elementos estruturais sem executar o módulo visitado."""

    def __init__(self) -> None:
        self.imports: list[ASTImport] = []
        self.classes: list[ASTClass] = []
        self.funcoes: list[ASTFunction] = []
        self.chamadas: list[ASTCall] = []
        self._classes_atuais: list[ASTClass] = []
        self._funcoes_atuais: list[ast.FunctionDef | ast.AsyncFunctionDef] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(ASTImport(modulo=alias.name, nomes=[]))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.imports.append(
            ASTImport(
                modulo=node.module or "",
                nomes=[alias.name for alias in node.names],
                import_relativo=node.level,
            )
        )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        classe = ASTClass(
            nome=node.name,
            linha=getattr(node, "lineno", None),
            decorators=[_expressao_para_texto(decorator) for decorator in node.decorator_list],
            bases=[_expressao_para_texto(base) for base in node.bases],
        )
        self.classes.append(classe)
        self._classes_atuais.append(classe)
        self.generic_visit(node)
        self._classes_atuais.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._registrar_funcao(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._registrar_funcao(node)

    def visit_Call(self, node: ast.Call) -> None:
        self.chamadas.append(
            ASTCall(
                nome=_nome_da_chamada(node.func),
                linha=getattr(node, "lineno", None),
            )
        )
        self.generic_visit(node)

    def _registrar_funcao(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        funcao = ASTFunction(
            nome=node.name,
            linha=getattr(node, "lineno", None),
            decorators=[_expressao_para_texto(decorator) for decorator in node.decorator_list],
            eh_metodo=bool(self._classes_atuais) and not self._funcoes_atuais,
        )
        self.funcoes.append(funcao)
        if self._classes_atuais and not self._funcoes_atuais:
            self._classes_atuais[-1].metodos.append(funcao)
        self._funcoes_atuais.append(node)
        self.generic_visit(node)
        self._funcoes_atuais.pop()


def _expressao_para_texto(node: ast.AST) -> str:
    """Representa uma expressão sem avaliá-la."""
    try:
        return ast.unparse(node)
    except AttributeError:
        return type(node).__name__


def _nome_da_chamada(node: ast.AST) -> str:
    """Obtém o nome de uma chamada sem incluir seus argumentos."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Call):
        return _nome_da_chamada(node.func)
    if isinstance(node, ast.Attribute):
        prefixo = _nome_da_chamada(node.value)
        return f"{prefixo}.{node.attr}"
    return _expressao_para_texto(node)


def analisar_arquivo(caminho: Path) -> ResultadoAST:
    """Analisa estaticamente um arquivo Python."""
    caminho = Path(caminho)
    codigo = caminho.read_text(encoding="utf-8")
    return analisar_codigo(codigo, caminho)


def analisar_codigo(codigo: str, caminho: Path | str = Path("<string>")) -> ResultadoAST:
    """Analisa código Python fornecido diretamente, sem executá-lo."""
    caminho = Path(caminho)
    try:
        arvore = ast.parse(codigo, filename=str(caminho))
    except SyntaxError as erro:
        return ResultadoAST(
            caminho=caminho,
            imports=[],
            classes=[],
            funcoes=[],
            chamadas=[],
            erro=erro.msg,
            linha_erro=erro.lineno,
            coluna_erro=erro.offset,
        )

    visitante = _Visitor()
    visitante.visit(arvore)
    return ResultadoAST(
        caminho=caminho,
        imports=visitante.imports,
        classes=visitante.classes,
        funcoes=visitante.funcoes,
        chamadas=visitante.chamadas,
    )
