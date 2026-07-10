import uuid
from collections.abc import AsyncIterator, Sequence

from fastapi import status

from app.conversa.historico import montar_historico
from app.conversa.repositorio import RepositorioDeConversas
from app.erros import ErroDaAplicacao
from app.limites.orcamento import OrcamentoDeTokens, OrcamentoEsgotado
from app.limites.tokens import estimar_tokens
from app.llm.base import MensagemDoModelo, ProvedorLLM
from app.rag.contexto import montar_instrucao
from app.rag.indice import IndiceDeDocumentos


class ServicoDeConversa:
    def __init__(
        self,
        repositorio: RepositorioDeConversas,
        provedor: ProvedorLLM,
        indice: IndiceDeDocumentos,
        orcamento: OrcamentoDeTokens,
    ) -> None:
        self._repositorio = repositorio
        self._provedor = provedor
        self._indice = indice
        self._orcamento = orcamento

    async def responder_em_pedacos(
        self, conversa_id: uuid.UUID, pergunta: str
    ) -> AsyncIterator[str]:
        """Valida conversa e orçamento antes de devolver o gerador: os dois
        precisam virar resposta HTTP, não um evento no meio do stream."""
        turnos = await self._preparar_turnos(conversa_id, pergunta)

        # A busca usa só a pergunta atual, não a conversa inteira: o histórico
        # antigo puxaria trechos do assunto anterior.
        trechos = await self._indice.buscar(pergunta)
        instrucao = montar_instrucao(trechos)

        # O contexto do RAG é a maior parte da conta, e é cobrado como entrada.
        tokens_entrada = estimar_tokens(instrucao) + sum(
            estimar_tokens(turno.conteudo) for turno in turnos
        )
        await self._reservar(conversa_id, tokens_entrada)

        return self._transmitir(conversa_id, pergunta, instrucao, turnos, tokens_entrada)

    async def _transmitir(
        self,
        conversa_id: uuid.UUID,
        pergunta: str,
        instrucao: str,
        turnos: Sequence[MensagemDoModelo],
        tokens_entrada: int,
    ) -> AsyncIterator[str]:
        pedacos: list[str] = []
        async for pedaco in self._provedor.gerar_stream(instrucao, turnos):
            pedacos.append(pedaco)
            yield pedaco

        resposta = "".join(pedacos).strip()
        tokens_saida = estimar_tokens(resposta)

        # A resposta não pode ser "desgerada" por ter passado do teto; só é
        # contabilizada, e a próxima pergunta será barrada.
        await self._orcamento.registrar_consumo(conversa_id, tokens_saida)

        # Só grava depois que a resposta terminou inteira. Uma falha no meio
        # deixa a conversa sem meia-resposta no histórico.
        await self._repositorio.registrar_troca(
            conversa_id, pergunta, resposta, tokens_entrada, tokens_saida
        )

    async def _reservar(self, conversa_id: uuid.UUID, tokens: int) -> None:
        try:
            await self._orcamento.reservar(conversa_id, tokens)
        except OrcamentoEsgotado as erro:
            raise ErroDaAplicacao(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "orcamento_esgotado",
                "Esta conversa atingiu o limite de uso. Comece uma nova conversa.",
            ) from erro

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
