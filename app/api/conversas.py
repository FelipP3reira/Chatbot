import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.documentos import obter_indice
from app.conversa.repositorio import RepositorioDeConversas
from app.conversa.servico import ServicoDeConversa
from app.db import obter_sessao
from app.llm.base import ProvedorIndisponivel, ProvedorLLM
from app.llm.fabrica import obter_provedor
from app.rag.indice import IndiceDeDocumentos

logger = logging.getLogger(__name__)

roteador = APIRouter(prefix="/conversas", tags=["conversas"])

TAMANHO_MAXIMO_DA_MENSAGEM = 4000
MENSAGEM_DE_FALLBACK = (
    "Não consegui responder agora — o serviço de IA não respondeu. "
    "Tente de novo em alguns instantes."
)


class RespostaConversaCriada(BaseModel):
    id: uuid.UUID


class PedidoDeMensagem(BaseModel):
    conteudo: str = Field(min_length=1, max_length=TAMANHO_MAXIMO_DA_MENSAGEM)


def obter_servico(
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
    provedor: Annotated[ProvedorLLM, Depends(obter_provedor)],
    indice: Annotated[IndiceDeDocumentos, Depends(obter_indice)],
) -> ServicoDeConversa:
    return ServicoDeConversa(RepositorioDeConversas(sessao), provedor, indice)


@roteador.post("", status_code=status.HTTP_201_CREATED, response_model=RespostaConversaCriada)
async def criar_conversa(
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
) -> RespostaConversaCriada:
    conversa = await RepositorioDeConversas(sessao).criar_conversa()
    return RespostaConversaCriada(id=conversa.id)


@roteador.post("/{conversa_id}/mensagens")
async def enviar_mensagem(
    conversa_id: uuid.UUID,
    pedido: PedidoDeMensagem,
    servico: Annotated[ServicoDeConversa, Depends(obter_servico)],
) -> StreamingResponse:
    pedacos = await servico.responder_em_pedacos(conversa_id, pedido.conteudo)
    return StreamingResponse(
        _eventos(pedacos),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _eventos(pedacos: AsyncIterator[str]) -> AsyncIterator[str]:
    try:
        async for pedaco in pedacos:
            yield _evento("pedaco", {"texto": pedaco})
        yield _evento("fim", {})
    except ProvedorIndisponivel:
        # O stream já começou com 200; o erro tem que viajar como evento.
        logger.warning("Provedor indisponível durante a resposta", exc_info=True)
        yield _evento("erro", {"mensagem": MENSAGEM_DE_FALLBACK})


def _evento(nome: str, dados: dict[str, Any]) -> str:
    # JSON também resolve o texto com quebra de linha, que partiria o evento.
    return f"event: {nome}\ndata: {json.dumps(dados, ensure_ascii=False)}\n\n"
