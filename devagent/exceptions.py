"""Exceções de domínio utilizadas pelo DevAgent."""


class DevAgentException(Exception):
    """Exceção base para falhas conhecidas do DevAgent."""


class CaminhoInvalidoError(DevAgentException, ValueError):
    """Indica que o caminho informado não pode ser usado como raiz.

    Args:
        mensagem: Descrição do motivo pelo qual o caminho é inválido.
    """


class CaminhoNaoPermitidoError(CaminhoInvalidoError):
    """Indica que um caminho está fora das raízes permitidas pelo MCP."""


class ErroVarreduraError(DevAgentException, RuntimeError):
    """Indica uma falha inesperada durante a preparação da varredura.

    Args:
        mensagem: Descrição da falha encontrada durante a varredura.
    """


