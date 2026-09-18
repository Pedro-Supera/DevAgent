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


class ArquivoNaoPermitidoError(DevAgentException, ValueError):
    """Indica que um arquivo não pode ser lido pela política de segurança."""


class ArquivoMuitoGrandeError(ArquivoNaoPermitidoError):
    """Indica que o arquivo excede o limite de leitura."""


class ArquivoBinarioError(ArquivoNaoPermitidoError):
    """Indica que o conteúdo não é texto UTF-8 válido."""


