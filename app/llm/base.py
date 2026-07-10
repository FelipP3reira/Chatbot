from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class MensagemDoModelo:
    """Uma virada de turno como o modelo enxerga — sem nada do banco."""

    papel: Literal["usuario", "assistente"]
    conteudo: str


class ProvedorLLM(Protocol):
    """Contrato mínimo. A resposta sempre chega em pedaços; quem não quer
    streaming junta os pedaços."""

    def gerar_stream(
        self, sistema: str, mensagens: Sequence[MensagemDoModelo]
    ) -> AsyncIterator[str]: ...


class ProvedorIndisponivel(Exception):
    """O provedor falhou de um jeito que não adianta insistir agora."""
