"""Modelos tipados usados pela varredura de projetos."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass(frozen=True)
class ItemEstrutura:
    """Representa um arquivo ou diretório encontrado no projeto.

    Args:
        caminho_relativo: Caminho da entrada relativo à raiz analisada.
        eh_diretorio: Indica se a entrada é um diretório.
        tamanho_bytes: Tamanho da entrada em bytes.
        extensao: Extensão do arquivo ou string vazia para diretórios.

    Raises:
        TypeError: Se algum campo tiver um tipo incompatível.
        ValueError: Se o tamanho for negativo.
    """

    caminho_relativo: Path
    eh_diretorio: bool
    tamanho_bytes: int
    extensao: str

    def __post_init__(self) -> None:
        """Valida os campos do item após sua criação.

        Raises:
            TypeError: Se algum campo tiver um tipo incompatível.
            ValueError: Se `tamanho_bytes` for negativo.
        """
        if not isinstance(self.caminho_relativo, Path):
            raise TypeError("caminho_relativo deve ser um pathlib.Path")
        if not isinstance(self.eh_diretorio, bool):
            raise TypeError("eh_diretorio deve ser bool")
        if not isinstance(self.tamanho_bytes, int) or isinstance(self.tamanho_bytes, bool):
            raise TypeError("tamanho_bytes deve ser int")
        if self.tamanho_bytes < 0:
            raise ValueError("tamanho_bytes não pode ser negativo")
        if not isinstance(self.extensao, str):
            raise TypeError("extensao deve ser str")


@dataclass
class ResultadoScanner:
    """Armazena o resultado completo de uma varredura de projeto.

    NOTA: Esta classe é mutável, ao contrário de `ItemEstrutura`. Campos como
    `total_arquivos` podem ser alterados após a criação, mas isso não é
    recomendado pelo fluxo normal do scanner.

    Args:
        raiz: Diretório absoluto usado como raiz da varredura.
        itens: Entradas encontradas durante a varredura.
        total_arquivos: Quantidade de arquivos encontrados.
        total_diretorios: Quantidade de diretórios encontrados.

    Raises:
        TypeError: Se algum campo tiver um tipo incompatível.
        ValueError: Se uma contagem for negativa.
    """

    raiz: Path
    itens: List[ItemEstrutura]
    total_arquivos: int
    total_diretorios: int

    def __post_init__(self) -> None:
        """Valida a consistência básica do resultado.

        Raises:
            TypeError: Se os campos não tiverem os tipos esperados.
            ValueError: Se uma contagem for negativa.
        """
        if not isinstance(self.raiz, Path):
            raise TypeError("raiz deve ser um pathlib.Path")
        if not isinstance(self.itens, list):
            raise TypeError("itens deve ser uma lista")
        if not all(isinstance(item, ItemEstrutura) for item in self.itens):
            raise TypeError("itens deve conter apenas ItemEstrutura")
        for nome, valor in (("total_arquivos", self.total_arquivos), ("total_diretorios", self.total_diretorios)):
            if not isinstance(valor, int) or isinstance(valor, bool):
                raise TypeError(f"{nome} deve ser int")
            if valor < 0:
                raise ValueError(f"{nome} não pode ser negativo")

    @property
    def estatisticas_extensao(self) -> Dict[str, Dict[str, Any]]:
        """Retorna estatísticas detalhadas por extensão de arquivo.

        Returns:
            Dicionário ordenado pela quantidade de arquivos em cada extensão.
        """
        contagem: Dict[str, int] = {}
        tamanho: Dict[str, int] = {}
        arquivos: Dict[str, int] = {}

        for item in self.itens:
            if item.eh_diretorio:
                continue
            ext = item.extensao or "(sem extensão)"
            contagem[ext] = contagem.get(ext, 0) + 1
            tamanho[ext] = tamanho.get(ext, 0) + item.tamanho_bytes
            arquivos[ext] = arquivos.get(ext, 0) + 1

        resultado: Dict[str, Dict[str, Any]] = {}
        for ext in contagem:
            resultado[ext] = {
                "quantidade": contagem[ext],
                "tamanho_total": tamanho[ext],
                "tamanho_medio": round(tamanho[ext] / contagem[ext], 2) if contagem[ext] else 0,
            }

        return dict(sorted(resultado.items(), key=lambda x: x[1]["quantidade"], reverse=True))

    @property
    def tamanho_total_bytes(self) -> int:
        """Retorna o tamanho total em bytes de todos os arquivos.

        Returns:
            Soma dos tamanhos dos arquivos encontrados.
        """
        return sum(item.tamanho_bytes for item in self.itens if not item.eh_diretorio)

    @property
    def extensao_mais_comum(self) -> str:
        """Retorna a extensão mais comum no projeto.

        Returns:
            Extensão com maior quantidade de arquivos ou ``"Nenhuma"``.
        """
        extensao = self.estatisticas_extensao
        if not extensao:
            return "Nenhuma"
        return next(iter(extensao))

    def para_json(self) -> str:
        """Exporta o resultado como JSON legível e determinístico.

        Returns:
            Texto JSON contendo a raiz, os itens e as métricas calculadas.
        """
        dados: dict[str, Any] = asdict(self)
        dados["raiz"] = str(self.raiz)
        dados["itens"] = [
            {
                "caminho_relativo": str(item.caminho_relativo),
                "eh_diretorio": item.eh_diretorio,
                "tamanho_bytes": item.tamanho_bytes,
                "extensao": item.extensao,
            }
            for item in self.itens
        ]
        dados["estatisticas_extensao"] = self.estatisticas_extensao
        dados["tamanho_total_bytes"] = self.tamanho_total_bytes
        return json.dumps(dados, ensure_ascii=False, indent=2)

    def para_arvore_texto(self) -> str:
        """Gera uma árvore textual semelhante ao comando ``tree``.

        Returns:
            Representação textual hierárquica dos itens encontrados.
        """
        linhas = [f"{self.raiz.name or self.raiz}/"]
        caminhos = sorted(
            self.itens,
            key=lambda item: (
                tuple(item.caminho_relativo.parts[:-1]),
                not item.eh_diretorio,
                item.caminho_relativo.name.lower(),
            ),
        )

        for item in caminhos:
            partes = item.caminho_relativo.parts
            prefixos: list[str] = []
            for nivel in range(len(partes) - 1):
                prefixos.append("    " if _nivel_tem_proximo_irmao(caminhos, partes[: nivel + 1]) else "│   ")
            marcador = "└── " if _ultimo_no_nivel(caminhos, partes) else "├── "
            linhas.append("".join(prefixos) + marcador + partes[-1] + ("/" if item.eh_diretorio else ""))

        return "\n".join(linhas)

    def buscar_por_extensao(self, extensao: str) -> List[ItemEstrutura]:
        """Busca arquivos pela extensão informada.

        Args:
            extensao: Extensão com ou sem ponto, como ``".py"`` ou ``"py"``.

        Returns:
            Lista de arquivos que possuem a extensão, preservando a ordem dos itens.

        Raises:
            TypeError: Se `extensao` não for uma string.
        """
        if not isinstance(extensao, str):
            raise TypeError("extensao deve ser str")
        normalizada = extensao if extensao.startswith(".") else f".{extensao}"
        normalizada = normalizada.lower()
        return [
            item for item in self.itens
            if not item.eh_diretorio and item.extensao.lower() == normalizada
        ]

    def buscar_por_tamanho(self, limite_bytes: int) -> List[ItemEstrutura]:
        """Busca arquivos com tamanho menor ou igual ao limite.

        Args:
            limite_bytes: Tamanho máximo permitido em bytes.

        Returns:
            Lista de arquivos com tamanho até `limite_bytes`.

        Raises:
            TypeError: Se `limite_bytes` não for um inteiro.
            ValueError: Se `limite_bytes` for negativo.
        """
        if not isinstance(limite_bytes, int) or isinstance(limite_bytes, bool):
            raise TypeError("limite_bytes deve ser int")
        if limite_bytes < 0:
            raise ValueError("limite_bytes não pode ser negativo")
        return [
            item for item in self.itens
            if not item.eh_diretorio and item.tamanho_bytes <= limite_bytes
        ]


def _ultimo_no_nivel(itens: list[ItemEstrutura], partes: tuple[str, ...]) -> bool:
    """Indica se o item é o último irmão dentro do diretório pai.

    Args:
        itens: Itens que compõem a árvore.
        partes: Componentes do caminho do item atual.

    Returns:
        `True` quando não há irmão posterior no mesmo nível.
    """
    candidatos = [item.caminho_relativo.parts for item in itens if len(item.caminho_relativo.parts) == len(partes)]
    mesmos_pais = [caminho for caminho in candidatos if caminho[:-1] == partes[:-1]]
    return mesmos_pais and mesmos_pais[-1] == partes


def _nivel_tem_proximo_irmao(itens: list[ItemEstrutura], partes: tuple[str, ...]) -> bool:
    """Indica se existe um item posterior no mesmo ramo da árvore.

    Args:
        itens: Itens que compõem a árvore.
        partes: Componentes do caminho do nível atual.

    Returns:
        `True` quando existe um irmão posterior no mesmo nível.
    """
    pais = partes[:-1]
    candidatos = [item.caminho_relativo.parts for item in itens if len(item.caminho_relativo.parts) == len(partes)]
    mesmos_pais = [caminho for caminho in candidatos if caminho[:-1] == pais]
    return bool(mesmos_pais and mesmos_pais[-1] != partes)


@dataclass(frozen=True)
class ASTImport:
    """Representa uma instrução ``import`` ou ``from ... import``.

    Args:
        modulo: Nome do módulo importado (ex.: ``os``, ``typing.List``).
        nomes: Nomes importados do módulo (lista vazia em ``import os``).
        import_relativo: Número de pontos em ``from .modulo import algo``.
    """

    modulo: str
    nomes: List[str]
    import_relativo: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.modulo, str):
            raise TypeError("modulo deve ser str")
        if not isinstance(self.nomes, list):
            raise TypeError("nomes deve ser lista")
        if not isinstance(self.import_relativo, int) or isinstance(self.import_relativo, bool):
            raise TypeError("import_relativo deve ser int")
        if self.import_relativo < 0:
            raise ValueError("import_relativo não pode ser negativo")


@dataclass(frozen=True)
class ASTClass:
    """Representa uma definição de classe.

    Args:
        nome: Nome da classe.
        linha: Linha de definição (1-indexed).
        decorators: Nomes dos decorators aplicados.
        bases: Nomes das classes base.
    """

    nome: str
    linha: int | None
    decorators: List[str]
    bases: List[str]
    metodos: List[ASTFunction] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.nome, str):
            raise TypeError("nome deve ser str")
        if self.linha is not None and (not isinstance(self.linha, int) or isinstance(self.linha, bool)):
            raise TypeError("linha deve ser int ou None")
        if not isinstance(self.decorators, list):
            raise TypeError("decorators deve ser lista")
        if not isinstance(self.bases, list):
            raise TypeError("bases deve ser lista")
        if not isinstance(self.metodos, list):
            raise TypeError("metodos deve ser lista")
        if not all(isinstance(item, ASTFunction) for item in self.metodos):
            raise TypeError("metodos deve conter apenas ASTFunction")


@dataclass(frozen=True)
class ASTFunction:
    """Representa uma definição de função ou método.

    Args:
        nome: Nome da função/método.
        linha: Linha de definição (1-indexed).
        decorators: Nomes dos decorators aplicados.
        eh_metodo: Indica se é método dentro de uma classe.
    """

    nome: str
    linha: int | None
    decorators: List[str]
    eh_metodo: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.nome, str):
            raise TypeError("nome deve ser str")
        if self.linha is not None and (not isinstance(self.linha, int) or isinstance(self.linha, bool)):
            raise TypeError("linha deve ser int ou None")
        if not isinstance(self.decorators, list):
            raise TypeError("decorators deve ser lista")
        if not isinstance(self.eh_metodo, bool):
            raise TypeError("eh_metodo deve ser bool")


@dataclass(frozen=True)
class ASTCall:
    """Representa uma chamada de função/método.

    Args:
        nome: Nome da função chamada (ou atributo acessado).
        linha: Linha da chamada (1-indexed).
    """

    nome: str
    linha: int | None

    def __post_init__(self) -> None:
        if not isinstance(self.nome, str):
            raise TypeError("nome deve ser str")
        if self.linha is not None and (not isinstance(self.linha, int) or isinstance(self.linha, bool)):
            raise TypeError("linha deve ser int ou None")


@dataclass(frozen=True)
class ResultadoAST:
    """Representa o resultado da análise estática de um arquivo Python.

    Args:
        caminho: Caminho do arquivo analisado.
        imports: Instruções de importação encontradas.
        classes: Classes definidas no arquivo.
        funcoes: Funções e métodos definidos no arquivo.
        chamadas: Chamadas de função ou método encontradas.
    """

    caminho: Path
    imports: List[ASTImport]
    classes: List[ASTClass]
    funcoes: List[ASTFunction]
    chamadas: List[ASTCall]
    erro: str | None = None
    linha_erro: int | None = None
    coluna_erro: int | None = None

    def __post_init__(self) -> None:
        """Valida a consistência básica do resultado."""
        if not isinstance(self.caminho, Path):
            raise TypeError("caminho deve ser um pathlib.Path")
        if not isinstance(self.imports, list):
            raise TypeError("imports deve ser lista")
        if not isinstance(self.classes, list):
            raise TypeError("classes deve ser lista")
        if not isinstance(self.funcoes, list):
            raise TypeError("funcoes deve ser lista")
        if not isinstance(self.chamadas, list):
            raise TypeError("chamadas deve ser lista")
        if not all(isinstance(item, ASTImport) for item in self.imports):
            raise TypeError("imports deve conter apenas ASTImport")
        if not all(isinstance(item, ASTClass) for item in self.classes):
            raise TypeError("classes deve conter apenas ASTClass")
        if not all(isinstance(item, ASTFunction) for item in self.funcoes):
            raise TypeError("funcoes deve conter apenas ASTFunction")
        if not all(isinstance(item, ASTCall) for item in self.chamadas):
            raise TypeError("chamadas deve conter apenas ASTCall")
        if self.erro is not None and not isinstance(self.erro, str):
            raise TypeError("erro deve ser str ou None")
        for nome, valor in (("linha_erro", self.linha_erro), ("coluna_erro", self.coluna_erro)):
            if valor is not None and (not isinstance(valor, int) or isinstance(valor, bool)):
                raise TypeError(f"{nome} deve ser int ou None")
