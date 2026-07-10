from collections.abc import AsyncIterator, Iterator, Sequence

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.api.conversas import MENSAGEM_DE_FALLBACK
from app.conversa.modelos import Mensagem
from app.db import criar_sessao
from app.llm.base import ErroTemporarioDoProvedor, MensagemDoModelo
from app.llm.fabrica import obter_provedor
from app.llm.resiliencia import ProvedorResiliente
from app.main import app
from tests.sse import ler_eventos, nomes_dos_eventos

_NADA: list[str] = []


class ProvedorSempreFora:
    async def gerar_stream(
        self, sistema: str, mensagens: Sequence[MensagemDoModelo]
    ) -> AsyncIterator[str]:
        for pedaco in _NADA:  # falha sem chegar a emitir pedaço nenhum
            yield pedaco
        raise ErroTemporarioDoProvedor("fora do ar")


@pytest.fixture
def provedor_fora() -> Iterator[None]:
    app.dependency_overrides[obter_provedor] = lambda: ProvedorResiliente(
        ProvedorSempreFora(), tentativas=2, espera_base_ms=1
    )
    yield
    app.dependency_overrides.clear()


async def test_provedor_fora_do_ar_vira_evento_de_erro(
    banco_limpo: None, provedor_fora: None
) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://teste") as cliente:
        conversa_id = (await cliente.post("/conversas")).json()["id"]
        resposta = await cliente.post(
            f"/conversas/{conversa_id}/mensagens", json={"conteudo": "oi"}
        )

    # O stream já respondeu 200 antes de o provedor falhar: o erro viaja como evento.
    assert resposta.status_code == 200
    assert nomes_dos_eventos(resposta.text) == ["erro"]

    ((_, dados),) = ler_eventos(resposta.text)
    assert dados["mensagem"] == MENSAGEM_DE_FALLBACK


async def test_resposta_falha_nao_entra_no_historico(
    banco_limpo: None, provedor_fora: None
) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://teste") as cliente:
        conversa_id = (await cliente.post("/conversas")).json()["id"]
        await cliente.post(f"/conversas/{conversa_id}/mensagens", json={"conteudo": "oi"})

    async with criar_sessao() as sessao:
        total = await sessao.scalar(select(func.count()).select_from(Mensagem))

    assert total == 0
