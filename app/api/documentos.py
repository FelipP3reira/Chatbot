import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import obter_sessao
from app.rag.embeddings import Embedder
from app.rag.fabrica import obter_embedder
from app.rag.indice import IndiceDeDocumentos

roteador = APIRouter(prefix="/documentos", tags=["documentos"])

TAMANHO_MAXIMO_DO_DOCUMENTO = 100_000


class PedidoDeIngestao(BaseModel):
    titulo: str = Field(min_length=1, max_length=300)
    conteudo: str = Field(min_length=1, max_length=TAMANHO_MAXIMO_DO_DOCUMENTO)
    origem: str | None = Field(default=None, max_length=500)


class RespostaDaIngestao(BaseModel):
    id: uuid.UUID
    titulo: str
    trechos: int


class ResumoDoDocumento(BaseModel):
    id: uuid.UUID
    titulo: str
    origem: str | None
    criado_em: datetime


def obter_indice(
    sessao: Annotated[AsyncSession, Depends(obter_sessao)],
    embedder: Annotated[Embedder, Depends(obter_embedder)],
) -> IndiceDeDocumentos:
    return IndiceDeDocumentos(sessao, embedder)


@roteador.post("", status_code=status.HTTP_201_CREATED, response_model=RespostaDaIngestao)
async def ingerir_documento(
    pedido: PedidoDeIngestao,
    indice: Annotated[IndiceDeDocumentos, Depends(obter_indice)],
) -> RespostaDaIngestao:
    documento = await indice.ingerir(pedido.titulo, pedido.conteudo, pedido.origem)
    return RespostaDaIngestao(
        id=documento.id, titulo=documento.titulo, trechos=len(documento.trechos)
    )


@roteador.get("", response_model=list[ResumoDoDocumento])
async def listar_documentos(
    indice: Annotated[IndiceDeDocumentos, Depends(obter_indice)],
) -> list[ResumoDoDocumento]:
    documentos = await indice.listar_documentos()
    return [
        ResumoDoDocumento(
            id=documento.id,
            titulo=documento.titulo,
            origem=documento.origem,
            criado_em=documento.criado_em,
        )
        for documento in documentos
    ]
