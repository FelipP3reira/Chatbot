from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import conversas, documentos, saude
from app.config import obter_configuracao
from app.erros import registrar_tratadores_de_erro
from app.seguranca import aplicar_cabecalhos_de_seguranca

PASTA_DO_FRONTEND = Path(__file__).resolve().parent.parent / "web"


def criar_aplicacao() -> FastAPI:
    configuracao = obter_configuracao()
    app = FastAPI(
        title="Chatbot",
        description="Chatbot com streaming, histórico por sessão e RAG.",
        version="0.1.0",
    )

    app.middleware("http")(aplicar_cabecalhos_de_seguranca)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=configuracao.origens_permitidas,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    registrar_tratadores_de_erro(app)
    app.include_router(saude.roteador)
    app.include_router(conversas.roteador)
    app.include_router(documentos.roteador)

    # Montado por último: as rotas da API têm precedência sobre os arquivos.
    app.mount("/", StaticFiles(directory=PASTA_DO_FRONTEND, html=True), name="web")
    return app


app = criar_aplicacao()
