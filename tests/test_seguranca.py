from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import PASTA_DO_FRONTEND, app
from tests.sse import ler_eventos, texto_recebido

ESCRITAS_PERIGOSAS = ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(")


@pytest.fixture
async def cliente(banco_limpo: None) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://teste")


def test_o_frontend_nunca_escreve_html_cru() -> None:
    """Guarda de regressão: a resposta do modelo pode carregar o texto de um
    documento enviado por outra pessoa. Escrever HTML seria XSS armazenado."""
    codigo = (PASTA_DO_FRONTEND / "app.js").read_text(encoding="utf-8")

    for escrita in ESCRITAS_PERIGOSAS:
        assert escrita not in codigo, f"{escrita} abre caminho para XSS no chat"


def test_a_pagina_nao_tem_script_nem_estilo_embutido() -> None:
    # A CSP recusa 'unsafe-inline'; um script embutido simplesmente não roda.
    pagina = (PASTA_DO_FRONTEND / "index.html").read_text(encoding="utf-8")

    assert "<script>" not in pagina
    assert "onclick=" not in pagina
    assert "<style>" not in pagina


async def test_respostas_trazem_os_cabecalhos_de_seguranca(cliente: AsyncClient) -> None:
    async with cliente:
        resposta = await cliente.get("/saude")

    politica = resposta.headers["content-security-policy"]
    assert "script-src 'self'" in politica
    assert "unsafe-inline" not in politica
    assert resposta.headers["x-content-type-options"] == "nosniff"
    assert resposta.headers["x-frame-options"] == "DENY"


async def test_a_pagina_e_servida_na_raiz(cliente: AsyncClient) -> None:
    async with cliente:
        resposta = await cliente.get("/")

    assert resposta.status_code == 200
    assert "<h1>Chatbot</h1>" in resposta.text


async def test_a_api_tem_precedencia_sobre_os_arquivos(cliente: AsyncClient) -> None:
    async with cliente:
        resposta = await cliente.get("/saude")

    assert resposta.json()["status"] == "ok"


async def test_script_na_pergunta_volta_como_texto_e_nao_como_html(cliente: AsyncClient) -> None:
    hostil = "<script>alert(1)</script>"

    async with cliente:
        conversa_id = (await cliente.post("/conversas")).json()["id"]
        resposta = await cliente.post(
            f"/conversas/{conversa_id}/mensagens", json={"conteudo": hostil}
        )

    # O provedor fake ecoa a pergunta. O texto atravessa o SSE dentro de JSON,
    # e o frontend o escreve com textContent — nunca é interpretado como marcação.
    assert hostil in texto_recebido(resposta.text)

    (nome, dados), *_ = ler_eventos(resposta.text)
    assert nome == "pedaco"
    assert isinstance(dados["texto"], str)


def test_a_pasta_do_frontend_existe_onde_a_aplicacao_procura() -> None:
    assert PASTA_DO_FRONTEND.is_dir()
    assert (PASTA_DO_FRONTEND / "index.html").is_file()


def test_o_env_de_exemplo_nao_traz_segredo() -> None:
    exemplo = Path(".env.example").read_text(encoding="utf-8")

    for linha in exemplo.splitlines():
        if linha.startswith("ANTHROPIC_API_KEY"):
            assert linha.strip() == "ANTHROPIC_API_KEY="


def test_a_mensagem_de_fallback_nao_vaza_detalhe_interno() -> None:
    from app.api.conversas import MENSAGEM_DE_FALLBACK

    for vazamento in ("Traceback", "anthropic", "api_key", "Exception"):
        assert vazamento not in MENSAGEM_DE_FALLBACK
