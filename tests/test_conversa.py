import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def cliente(banco_limpo: None) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://teste")


async def _criar_conversa(cliente: AsyncClient) -> str:
    resposta = await cliente.post("/conversas")
    assert resposta.status_code == 201
    return str(resposta.json()["id"])


async def test_responde_e_guarda_a_troca(cliente: AsyncClient) -> None:
    async with cliente:
        conversa_id = await _criar_conversa(cliente)

        resposta = await cliente.post(
            f"/conversas/{conversa_id}/mensagens", json={"conteudo": "oi"}
        )

        assert resposta.status_code == 200
        assert resposta.json()["resposta"] == "Você disse: oi"


async def test_historico_alimenta_a_proxima_pergunta(cliente: AsyncClient) -> None:
    async with cliente:
        conversa_id = await _criar_conversa(cliente)
        await cliente.post(f"/conversas/{conversa_id}/mensagens", json={"conteudo": "primeira"})

        segunda = await cliente.post(
            f"/conversas/{conversa_id}/mensagens", json={"conteudo": "segunda"}
        )

        # O provedor fake ecoa a última fala do usuário; se o histórico tivesse
        # se perdido, a ordem das mensagens não se sustentaria.
        assert segunda.json()["resposta"] == "Você disse: segunda"


async def test_conversa_inexistente_devolve_404(cliente: AsyncClient) -> None:
    async with cliente:
        resposta = await cliente.post(
            f"/conversas/{uuid.uuid4()}/mensagens", json={"conteudo": "oi"}
        )

    assert resposta.status_code == 404
    assert resposta.json()["erro"]["codigo"] == "conversa_nao_encontrada"


async def test_mensagem_vazia_e_recusada(cliente: AsyncClient) -> None:
    async with cliente:
        conversa_id = await _criar_conversa(cliente)
        resposta = await cliente.post(f"/conversas/{conversa_id}/mensagens", json={"conteudo": ""})

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "entrada_invalida"


async def test_mensagem_longa_demais_e_recusada(cliente: AsyncClient) -> None:
    async with cliente:
        conversa_id = await _criar_conversa(cliente)
        resposta = await cliente.post(
            f"/conversas/{conversa_id}/mensagens", json={"conteudo": "a" * 4001}
        )

    assert resposta.status_code == 422
