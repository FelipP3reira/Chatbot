from collections.abc import AsyncIterator, Sequence
from typing import Literal

from anthropic import AsyncAnthropic
from anthropic.types import MessageParam

from app.llm.base import MensagemDoModelo

MAX_TOKENS_DA_RESPOSTA = 2048


class ProvedorAnthropic:
    """Claude via API. O raciocínio estendido fica desligado: numa conversa a
    latência do primeiro token importa mais que a profundidade."""

    def __init__(self, chave: str, modelo: str) -> None:
        self._cliente = AsyncAnthropic(api_key=chave)
        self._modelo = modelo

    async def gerar_stream(
        self, sistema: str, mensagens: Sequence[MensagemDoModelo]
    ) -> AsyncIterator[str]:
        async with self._cliente.messages.stream(
            model=self._modelo,
            max_tokens=MAX_TOKENS_DA_RESPOSTA,
            system=sistema,
            messages=[_para_a_api(mensagem) for mensagem in mensagens],
        ) as fluxo:
            async for texto in fluxo.text_stream:
                yield texto


def _para_a_api(mensagem: MensagemDoModelo) -> MessageParam:
    papel: Literal["user", "assistant"] = "user" if mensagem.papel == "usuario" else "assistant"
    return {"role": papel, "content": mensagem.conteudo}
