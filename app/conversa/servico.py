import uuid
from collections.abc import AsyncIterator, Sequence

from fastapi import status

from app.conversa.historico import montar_historico
from app.conversa.repositorio import RepositorioDeConversas
from app.erros import ErroDaAplicacao
from app.llm.base import MensagemDoModelo, ProvedorLLM
from app.rag.contexto import montar_instrucao
from app.rag.indice import IndiceDeDocumentos


class ServicoDeConversa:
    def __init__(
        self,
        repositorio: RepositorioDeConversas,
        provedor: ProvedorLLM,
        indice: IndiceDeDocumentos,
    ) -> None:
        self._repositorio = repositorio
        self._provedor = provedor
        self._indice = indice

    async def responder_em_pedacos(
        self, conversa_id: uuid.UUID, pergunta: str
    ) -> AsyncIterator[str]:
        """Valida a conversa antes de devolver o gerador: um 404 precisa virar
        resposta HTTP, não um evento no meio do stream."""
        turnos = await self._preparar_turnos(conversa_id, pergunta)

        # A busca usa só a pergunta atual, não a conversa inteira: o histórico
        # antigo puxaria trechos do assunto anterior.
        trechos = await self._indice.buscar(pergunta)
        instrucao = montar_instrucao(trechos)

        return self._transmitir(conversa_id, pergunta, instrucao, turnos)

    async def _transmitir(
        self,
        conversa_id: uuid.UUID,
        pergunta: str,
        instrucao: str,
        turnos: Sequence[MensagemDoModelo],
    ) -> AsyncIterator[str]:
        pedacos: list[str] = []
        async for pedaco in self._provedor.gerar_stream(instrucao, turnos):
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
