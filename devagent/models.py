"""Modelos tipados usados pela varredura de projetos."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
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
