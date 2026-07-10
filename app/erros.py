import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ErroDaAplicacao(Exception):
    """Erro previsto, com resposta pronta para o cliente."""

    def __init__(
        self,
        status_http: int,
        codigo: str,
        mensagem: str,
        detalhes: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(mensagem)
        self.status_http = status_http
        self.codigo = codigo
        self.mensagem = mensagem
        self.detalhes = detalhes


def _corpo(codigo: str, mensagem: str, detalhes: list[dict[str, Any]] | None) -> dict[str, Any]:
    return {"erro": {"codigo": codigo, "mensagem": mensagem, "detalhes": detalhes}}


def registrar_tratadores_de_erro(app: FastAPI) -> None:
    @app.exception_handler(ErroDaAplicacao)
    async def _erro_previsto(_: Request, erro: ErroDaAplicacao) -> JSONResponse:
        return JSONResponse(
            status_code=erro.status_http,
            content=_corpo(erro.codigo, erro.mensagem, erro.detalhes),
        )

    @app.exception_handler(RequestValidationError)
    async def _entrada_invalida(_: Request, erro: RequestValidationError) -> JSONResponse:
        detalhes = [
            {"campo": ".".join(str(parte) for parte in falha["loc"]), "problema": falha["msg"]}
            for falha in erro.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_corpo("entrada_invalida", "Os dados enviados não são válidos.", detalhes),
        )

    @app.exception_handler(Exception)
    async def _erro_inesperado(_: Request, erro: Exception) -> JSONResponse:
        # O traceback fica no log do servidor; o cliente nunca vê detalhe interno.
        logger.exception("Erro não tratado", exc_info=erro)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_corpo("erro_interno", "Algo deu errado do nosso lado.", None),
        )
