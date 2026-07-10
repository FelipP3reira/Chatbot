import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversa.repositorio import RepositorioDeConversas
from app.conversa.servico import ServicoDeConversa
from app.db import obter_sessao
from app.llm.base import ProvedorLLM
from app.llm.fabrica import obter_provedor

roteador = APIRouter(prefix="/conversas", tags=["conversas"])

TAMANHO_MAXIMO_DA_MENSAGEM = 4000


class RespostaConversaCriada(BaseModel):
    id: uuid.UUID


class PedidoDeMensagem(BaseModel):
    conteudo: str = Field(min_length=1, max_length=TAMANHO_MAXIMO_DA_MENSAGEM)


class RespostaDaMensagem(BaseModel):
    resposta: str


def obter_servico(
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
    provedor: Annotated[ProvedorLLM, Depends(obter_provedor)],
) -> ServicoDeConversa:
    return ServicoDeConversa(RepositorioDeConversas(sessao), provedor)


@roteador.post("", status_code=status.HTTP_201_CREATED, response_model=RespostaConversaCriada)
async def criar_conversa(
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
) -> RespostaConversaCriada:
    conversa = await RepositorioDeConversas(sessao).criar_conversa()
    return RespostaConversaCriada(id=conversa.id)


@roteador.post("/{conversa_id}/mensagens", response_model=RespostaDaMensagem)
async def enviar_mensagem(
    conversa_id: uuid.UUID,
    pedido: PedidoDeMensagem,
    servico: Annotated[ServicoDeConversa, Depends(obter_servico)],
) -> RespostaDaMensagem:
    resposta = await servico.responder(conversa_id, pedido.conteudo)
    return RespostaDaMensagem(resposta=resposta)
