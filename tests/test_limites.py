import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.config import obter_configuracao
from app.conversa.modelos import Conversa
from app.db import criar_sessao
from app.main import app


@pytest.fixture
async def cliente(banco_limpo: None) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://teste")


def _ajustar(monkeypatch: pytest.MonkeyPatch, variavel: str, valor: str) -> None:
    monkeypatch.setenv(variavel, valor)
    obter_configuracao.cache_clear()


async def _nova_conversa(cliente: AsyncClient) -> str:
    return str((await cliente.post("/conversas")).json()["id"])


async def _enviar(cliente: AsyncClient, conversa_id: str) -> int:
    resposta = await cliente.post(f"/conversas/{conversa_id}/mensagens", json={"conteudo": "oi"})
    return resposta.status_code


async def test_conversa_martelada_e_barrada(
    cliente: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ajustar(monkeypatch, "MENSAGENS_POR_MINUTO_POR_CONVERSA", "2")

    async with cliente:
        conversa_id = await _nova_conversa(cliente)

        assert await _enviar(cliente, conversa_id) == 200
        assert await _enviar(cliente, conversa_id) == 200

        resposta = await cliente.post(
            f"/conversas/{conversa_id}/mensagens", json={"conteudo": "oi"}
        )

    assert resposta.status_code == 429
    assert resposta.json()["erro"]["codigo"] == "muitas_requisicoes"


async def test_o_limite_de_uma_conversa_nao_afeta_a_outra(
    cliente: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ajustar(monkeypatch, "MENSAGENS_POR_MINUTO_POR_CONVERSA", "1")

    async with cliente:
        primeira = await _nova_conversa(cliente)
        segunda = await _nova_conversa(cliente)

        assert await _enviar(cliente, primeira) == 200
        assert await _enviar(cliente, primeira) == 429
        assert await _enviar(cliente, segunda) == 200


async def test_abrir_conversas_novas_nao_escapa_do_limite_por_ip(
    cliente: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ajustar(monkeypatch, "MENSAGENS_POR_MINUTO_POR_IP", "2")

    async with cliente:
        codigos = [await _enviar(cliente, await _nova_conversa(cliente)) for _ in range(3)]

    assert codigos == [200, 200, 429]


async def test_conversa_que_estoura_o_teto_de_tokens_e_barrada(
    cliente: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Um teto de 5 tokens não cobre nem a instrução do sistema.
    _ajustar(monkeypatch, "TETO_DE_TOKENS_POR_CONVERSA", "5")

    async with cliente:
        conversa_id = await _nova_conversa(cliente)
        resposta = await cliente.post(
            f"/conversas/{conversa_id}/mensagens", json={"conteudo": "oi"}
        )

    assert resposta.status_code == 429
    assert resposta.json()["erro"]["codigo"] == "orcamento_esgotado"


async def test_orcamento_acumula_e_barra_a_pergunta_seguinte(
    cliente: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Cabe uma troca, não duas.
    _ajustar(monkeypatch, "TETO_DE_TOKENS_POR_CONVERSA", "70")

    async with cliente:
        conversa_id = await _nova_conversa(cliente)

        assert await _enviar(cliente, conversa_id) == 200
        assert await _enviar(cliente, conversa_id) == 429


async def test_consumo_da_troca_fica_gravado_na_conversa(cliente: AsyncClient) -> None:
    async with cliente:
        conversa_id = await _nova_conversa(cliente)
        assert await _enviar(cliente, conversa_id) == 200

    async with criar_sessao() as sessao:
        conversa = (await sessao.scalars(select(Conversa))).one()

    assert conversa.tokens_entrada > 0
    assert conversa.tokens_saida > 0
