from collections.abc import AsyncIterator, Sequence

from app.llm.base import MensagemDoModelo


class ProvedorFake:
    """Responde sem rede, de forma determinística. Sustenta os testes e permite
    rodar o projeto inteiro sem chave de API."""

    def __init__(self, resposta: str | None = None) -> None:
        self._resposta = resposta

    async def gerar_stream(
        self, sistema: str, mensagens: Sequence[MensagemDoModelo]
    ) -> AsyncIterator[str]:
        for pedaco in self._montar_resposta(mensagens).split(" "):
            yield pedaco + " "

    def _montar_resposta(self, mensagens: Sequence[MensagemDoModelo]) -> str:
        if self._resposta is not None:
            return self._resposta
        ultima = next(
            (m.conteudo for m in reversed(mensagens) if m.papel == "usuario"),
            "",
        )
        return f"Você disse: {ultima}"
