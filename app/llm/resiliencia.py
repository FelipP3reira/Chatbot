import asyncio
import logging
import random
from collections.abc import AsyncIterator, Sequence

from app.llm.base import (
    ErroTemporarioDoProvedor,
    MensagemDoModelo,
    ProvedorIndisponivel,
    ProvedorLLM,
)

logger = logging.getLogger(__name__)

TENTATIVAS_PADRAO = 3
ESPERA_BASE_MS = 300
SEGUNDOS_SEM_PEDACO = 30.0


class ProvedorResiliente:
    """Envolve um provedor com timeout e retry, e traduz a desistência numa
    exceção única para quem chama."""

    def __init__(
        self,
        provedor: ProvedorLLM,
        tentativas: int = TENTATIVAS_PADRAO,
        espera_base_ms: int = ESPERA_BASE_MS,
        segundos_sem_pedaco: float = SEGUNDOS_SEM_PEDACO,
    ) -> None:
        self._provedor = provedor
        self._tentativas = tentativas
        self._espera_base_ms = espera_base_ms
        self._segundos_sem_pedaco = segundos_sem_pedaco

    async def gerar_stream(
        self, sistema: str, mensagens: Sequence[MensagemDoModelo]
    ) -> AsyncIterator[str]:
        for tentativa in range(1, self._tentativas + 1):
            ja_emitiu = False
            try:
                origem = self._provedor.gerar_stream(sistema, mensagens)
                async for pedaco in self._com_limite_de_espera(origem):
                    ja_emitiu = True
                    yield pedaco
                return
            except ErroTemporarioDoProvedor as erro:
                # Depois do primeiro pedaço no ar, repetir duplicaria a resposta
                # na tela: não dá para "desdizer" o que o usuário já leu.
                if ja_emitiu:
                    raise ProvedorIndisponivel("falhou no meio da resposta") from erro
                if tentativa == self._tentativas:
                    raise ProvedorIndisponivel("tentativas esgotadas") from erro

                espera = self._espera(tentativa)
                logger.warning(
                    "Provedor falhou (tentativa %d/%d); repetindo em %.2fs",
                    tentativa,
                    self._tentativas,
                    espera,
                )
                await asyncio.sleep(espera)

    async def _com_limite_de_espera(self, origem: AsyncIterator[str]) -> AsyncIterator[str]:
        """O limite é por pedaço, não pela resposta inteira: uma resposta longa
        é legítima, um provedor mudo não."""
        iterador = origem.__aiter__()
        while True:
            try:
                async with asyncio.timeout(self._segundos_sem_pedaco):
                    pedaco = await iterador.__anext__()
            except StopAsyncIteration:
                return
            except TimeoutError as erro:
                raise ErroTemporarioDoProvedor("o provedor parou de responder") from erro
            yield pedaco

    def _espera(self, tentativa: int) -> float:
        exponencial: int = self._espera_base_ms * (1 << (tentativa - 1))
        # O jitter espalha as tentativas de clientes que caíram juntos.
        jitter: float = random.uniform(0, self._espera_base_ms)
        return (exponencial + jitter) / 1000
