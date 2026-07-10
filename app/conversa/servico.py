import uuid
from collections.abc import AsyncIterator, Sequence

from fastapi import status

from app.conversa.historico import montar_historico
from app.conversa.repositorio import RepositorioDeConversas
from app.erros import ErroDaAplicacao
from app.llm.base import MensagemDoModelo, ProvedorLLM

INSTRUCAO_DO_SISTEMA = (
    "Você é um assistente prestativo e direto. Responda em português do Brasil. "
    "Quando não souber algo, diga que não sabe em vez de inventar."
)


class ServicoDeConversa:
    def __init__(self, repositorio: RepositorioDeConversas, provedor: ProvedorLLM) -> None:
        self._repositorio = repositorio
        self._provedor = provedor

    async def responder_em_pedacos(
        self, conversa_id: uuid.UUID, pergunta: str
    ) -> AsyncIterator[str]:
        """Valida a conversa antes de devolver o gerador: um 404 precisa virar
        resposta HTTP, não um evento no meio do stream."""
        turnos = await self._preparar_turnos(conversa_id, pergunta)
        return self._transmitir(conversa_id, pergunta, turnos)

    async def _transmitir(
        self, conversa_id: uuid.UUID, pergunta: str, turnos: Sequence[MensagemDoModelo]
    ) -> AsyncIterator[str]:
        pedacos: list[str] = []
        async for pedaco in self._provedor.gerar_stream(INSTRUCAO_DO_SISTEMA, turnos):
            pedacos.append(pedaco)
            yield pedaco

        # Só grava depois que a resposta terminou inteira. Uma falha no meio
        # deixa a conversa sem meia-resposta no histórico.
        await self._repositorio.registrar_troca(conversa_id, pergunta, "".join(pedacos).strip())

    async def _preparar_turnos(
        self, conversa_id: uuid.UUID, pergunta: str
    ) -> list[MensagemDoModelo]:
        if await self._repositorio.buscar_conversa(conversa_id) is None:
            raise ErroDaAplicacao(
                status.HTTP_404_NOT_FOUND,
                "conversa_nao_encontrada",
                "Essa conversa não existe.",
            )

        anteriores = await self._repositorio.listar_mensagens(conversa_id)
        historico = montar_historico(anteriores)
        return [*historico, MensagemDoModelo(papel="usuario", conteudo=pergunta)]
