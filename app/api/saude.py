from fastapi import APIRouter
from pydantic import BaseModel

from app.config import obter_configuracao

roteador = APIRouter(tags=["saúde"])


class RespostaSaude(BaseModel):
    status: str
    ambiente: str


@roteador.get("/saude", response_model=RespostaSaude)
async def verificar_saude() -> RespostaSaude:
    return RespostaSaude(status="ok", ambiente=obter_configuracao().ambiente)
