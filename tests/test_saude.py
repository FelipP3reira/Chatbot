from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_saude_responde_ok() -> None:
    transporte = ASGITransport(app=app)
    async with AsyncClient(transport=transporte, base_url="http://teste") as cliente:
        resposta = await cliente.get("/saude")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "ambiente": "teste"}


async def test_rota_inexistente_devolve_404() -> None:
    transporte = ASGITransport(app=app)
    async with AsyncClient(transport=transporte, base_url="http://teste") as cliente:
        resposta = await cliente.get("/nao-existe")

    assert resposta.status_code == 404
