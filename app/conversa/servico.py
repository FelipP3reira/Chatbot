import uuid

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

    async def responder(self, conversa_id: uuid.UUID, pergunta: str) -> str:
        turnos = await self._preparar_turnos(conversa_id, pergunta)

        pedacos = [
            pedaco async for pedaco in self._provedor.gerar_stream(INSTRUCAO_DO_SISTEMA, turnos)
        ]
        resposta = "".join(pedacos).strip()

        await self._repositorio.registrar_troca(conversa_id, pergunta, resposta)
        return resposta

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
