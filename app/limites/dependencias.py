import uuid
from typing import Annotated

from fastapi import Depends, Request, status
from redis.asyncio import Redis

from app.config import Configuracao, obter_configuracao
from app.erros import ErroDaAplicacao
from app.limites.orcamento import OrcamentoDeTokens
from app.limites.rate_limit import LimitadorDeTaxa
from app.limites.redis_cliente import obter_redis

JANELA_EM_SEGUNDOS = 60


def obter_orcamento(
    redis: Annotated[Redis, Depends(obter_redis)],
    configuracao: Annotated[Configuracao, Depends(obter_configuracao)],
) -> OrcamentoDeTokens:
    return OrcamentoDeTokens(
        redis,
        teto=configuracao.teto_de_tokens_por_conversa,
        validade_segundos=configuracao.validade_do_orcamento_segundos,
    )


async def limitar_taxa(
    conversa_id: uuid.UUID,
    requisicao: Request,
    redis: Annotated[Redis, Depends(obter_redis)],
    configuracao: Annotated[Configuracao, Depends(obter_configuracao)],
) -> None:
    """Dois limites, porque protegem de coisas diferentes: o do IP contém quem
    abre conversas novas em série; o da conversa contém quem martela uma só."""
    limites = (
        (f"ip:{_endereco(requisicao)}", configuracao.mensagens_por_minuto_por_ip),
        (f"conversa:{conversa_id}", configuracao.mensagens_por_minuto_por_conversa),
    )

    for chave, limite in limites:
        limitador = LimitadorDeTaxa(redis, limite=limite, janela_segundos=JANELA_EM_SEGUNDOS)
        if not await limitador.permitir(chave):
            raise ErroDaAplicacao(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "muitas_requisicoes",
                "Você está enviando mensagens rápido demais. Espere um instante.",
            )


def _endereco(requisicao: Request) -> str:
    # X-Forwarded-For é escrito pelo cliente e só vale atrás de um proxy que o
    # sobrescreva. Sem essa garantia, confiar nele deixaria qualquer um forjar
    # o próprio IP e escapar do limite.
    return requisicao.client.host if requisicao.client else "desconhecido"
