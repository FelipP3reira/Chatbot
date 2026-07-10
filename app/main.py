from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import saude
from app.config import obter_configuracao
from app.erros import registrar_tratadores_de_erro


def criar_aplicacao() -> FastAPI:
    configuracao = obter_configuracao()
    app = FastAPI(
        title="Chatbot",
        description="Chatbot com streaming, histórico por sessão e RAG.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=configuracao.origens_permitidas,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    registrar_tratadores_de_erro(app)
    app.include_router(saude.roteador)
    return app


app = criar_aplicacao()
